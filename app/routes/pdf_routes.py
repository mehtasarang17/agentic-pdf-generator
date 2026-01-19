"""API routes for PDF generation."""

import logging
import os
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file

from app.agents.orchestrator import orchestrate_pdf_generation
from app.config import config
from app.models.pdf import PDFDocument
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate a PDF from JSON input.

    Request Body:
    {
        "client_name": "Optional client name",
        "data": {
            "section_name": {
                "type": "analytics" or "descriptive",
                "content": {...}
            }
        }
    }

    Returns:
        JSON with status, pdf_url, and metadata
    """
    try:
        # Get JSON input
        input_data = request.get_json()

        if not input_data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400

        client_name = input_data.get('client_name')
        display_client_name = client_name if client_name else 'client_name_not_specified'
        logger.info(f"Received PDF generation request: {display_client_name}")

        # Run the workflow
        final_state = orchestrate_pdf_generation(input_data)

        # Check for errors
        if final_state.get('error'):
            return jsonify({
                'status': 'error',
                'message': final_state['error'],
                'validation_errors': final_state.get('validation_errors', [])
            }), 400

        # Check for PDF result
        pdf_result = final_state.get('pdf_result')
        if not pdf_result:
            return jsonify({
                'status': 'error',
                'message': 'PDF generation failed - no result produced'
            }), 500

        # Get file size
        pdf_id = pdf_result['pdf_id']
        file_path = config.PDF_OUTPUT_DIR / f"{pdf_id}.pdf"
        file_size = os.path.getsize(file_path) if file_path.exists() else 0

        # Save to database
        try:
            DatabaseService.create_pdf_record(
                pdf_id=pdf_id,
                filename=f"{pdf_id}.pdf",
                client_name=display_client_name,
                title=pdf_result['metadata'].get('title'),
                pages=pdf_result['metadata'].get('pages'),
                file_size=file_size,
                sections=pdf_result['metadata'].get('sections'),
                input_data=input_data.get('data'),
                status='completed'
            )
            logger.info(f"PDF record saved to database: {pdf_id}")
        except Exception as db_error:
            logger.error(f"Failed to save PDF record to database: {db_error}")

        # Return success response
        return jsonify({
            'status': 'success',
            'pdf_url': f"/api/v1/download/{pdf_id}",
            'metadata': pdf_result['metadata']
        }), 200

    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500


@pdf_bp.route('/download/<pdf_id>', methods=['GET'])
def download_pdf(pdf_id: str):
    """Download a generated PDF.

    Args:
        pdf_id: UUID of the generated PDF

    Returns:
        PDF file or error response
    """
    try:
        # Validate PDF ID format (basic UUID validation)
        if not pdf_id or len(pdf_id) != 36:
            return jsonify({
                'status': 'error',
                'message': 'Invalid PDF ID format'
            }), 400

        # Construct file path
        file_path = config.PDF_OUTPUT_DIR / f"{pdf_id}.pdf"

        if not file_path.exists():
            return jsonify({
                'status': 'error',
                'message': 'PDF not found'
            }), 404

        # Get title from database for filename
        pdf_doc = DatabaseService.get_pdf_by_id(pdf_id)
        download_name = f"report_{pdf_id[:8]}.pdf"
        if pdf_doc and pdf_doc.title:
            safe_title = "".join(c for c in pdf_doc.title if c.isalnum() or c in (' ', '-', '_')).strip()
            download_name = f"{safe_title[:50]}.pdf" if safe_title else download_name

        logger.info(f"Serving PDF: {pdf_id}")

        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        logger.error(f"PDF download error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error downloading PDF: {str(e)}'
        }), 500


@pdf_bp.route('/pdfs', methods=['GET'])
def list_pdfs():
    """List all generated PDFs.

    Query Parameters:
        - limit: Maximum number of PDFs to return (default: 100)
        - offset: Number of PDFs to skip (default: 0)
        - client: Filter by client name

    Returns:
        JSON with list of PDF metadata
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        client_name = request.args.get('client')

        if client_name:
            pdf_docs = DatabaseService.get_pdfs_by_client(client_name)
        else:
            pdf_docs = DatabaseService.get_all_pdfs(limit=limit, offset=offset)

        pdfs = [pdf.to_dict() for pdf in pdf_docs]

        return jsonify({
            'status': 'success',
            'count': len(pdfs),
            'pdfs': pdfs
        }), 200

    except Exception as e:
        logger.error(f"List PDFs error: {e}")
        # Fallback to file-based listing if database fails
        try:
            pdf_dir = config.PDF_OUTPUT_DIR
            pdf_files = list(pdf_dir.glob("*.pdf"))

            pdfs = []
            for pdf_file in pdf_files:
                pdfs.append({
                    'id': pdf_file.stem,
                    'filename': pdf_file.name,
                    'created_at': pdf_file.stat().st_mtime,
                    'size': pdf_file.stat().st_size,
                    'download_url': f"/api/v1/download/{pdf_file.stem}"
                })

            pdfs.sort(key=lambda x: x['created_at'], reverse=True)

            return jsonify({
                'status': 'success',
                'count': len(pdfs),
                'pdfs': pdfs,
                'source': 'filesystem'
            }), 200
        except Exception as file_error:
            logger.error(f"Fallback list PDFs error: {file_error}")
            return jsonify({
                'status': 'error',
                'message': f'Error listing PDFs: {str(e)}'
            }), 500


@pdf_bp.route('/delete/<pdf_id>', methods=['DELETE'])
def delete_pdf(pdf_id: str):
    """Delete a generated PDF.

    Args:
        pdf_id: UUID of the PDF to delete

    Returns:
        JSON with status
    """
    try:
        file_path = config.PDF_OUTPUT_DIR / f"{pdf_id}.pdf"

        if not file_path.exists():
            return jsonify({
                'status': 'error',
                'message': 'PDF not found'
            }), 404

        # Delete from filesystem
        file_path.unlink()
        logger.info(f"Deleted PDF file: {pdf_id}")

        # Delete from database
        try:
            DatabaseService.delete_pdf(pdf_id)
            logger.info(f"Deleted PDF record from database: {pdf_id}")
        except Exception as db_error:
            logger.warning(f"Could not delete PDF record from database: {db_error}")

        return jsonify({
            'status': 'success',
            'message': f'PDF {pdf_id} deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Delete PDF error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error deleting PDF: {str(e)}'
        }), 500


@pdf_bp.route('/pdf/<pdf_id>', methods=['GET'])
def get_pdf_details(pdf_id: str):
    """Get detailed information about a specific PDF.

    Args:
        pdf_id: UUID of the PDF

    Returns:
        JSON with PDF metadata
    """
    try:
        pdf_doc = DatabaseService.get_pdf_by_id(pdf_id)

        if not pdf_doc:
            return jsonify({
                'status': 'error',
                'message': 'PDF not found'
            }), 404

        return jsonify({
            'status': 'success',
            'pdf': pdf_doc.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Get PDF details error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting PDF details: {str(e)}'
        }), 500
