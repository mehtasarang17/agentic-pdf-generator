"""API routes for PDF generation."""

import logging
import os
import json
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file

from app.agents.orchestrator import orchestrate_pdf_generation
from app.config import config
from app.models.pdf import PDFDocument
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

pdf_bp = Blueprint('pdf', __name__)

def _coerce_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def _count_numeric_values(value, sample_limit=2000):
    numeric_count = 0
    total_count = 0
    stack = [value]

    while stack and total_count < sample_limit:
        current = stack.pop()
        if isinstance(current, dict):
            stack.extend(list(current.values()))
            continue
        if isinstance(current, list):
            stack.extend(current)
            continue
        total_count += 1
        if _coerce_number(current) is not None:
            numeric_count += 1

    return numeric_count, total_count

def _maybe_parse_json_string(value):
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed or trimmed[0] not in "{[" or trimmed[-1] not in "}]":
        return None
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return None

def _normalize_section_value(value):
    """Normalize a raw section value into the expected schema."""
    if isinstance(value, dict) and 'type' in value and 'content' in value:
        section_type = value.get('type') if value.get('type') in ('analytics', 'descriptive') else 'descriptive'
        content = value.get('content') if isinstance(value.get('content'), dict) else {'value': value.get('content')}
        return {'type': section_type, 'content': content}

    if isinstance(value, str):
        parsed = _maybe_parse_json_string(value)
        if isinstance(parsed, dict):
            has_structured_keys = any(
                key in parsed for key in ("description", "bullets", "findings", "summary")
            )
            if has_structured_keys:
                return {'type': 'descriptive', 'content': parsed}
            value = parsed

    if isinstance(value, dict):
        numeric_count, total_count = _count_numeric_values(value)
        is_analytic = numeric_count >= 2 and (total_count == 0 or numeric_count / total_count >= 0.2)
        section_type = 'analytics' if is_analytic else 'descriptive'
        return {'type': section_type, 'content': value}

    if isinstance(value, list):
        numeric_count, total_count = _count_numeric_values(value)
        is_analytic = numeric_count >= 2 and (total_count == 0 or numeric_count / total_count >= 0.2)
        if is_analytic:
            return {'type': 'analytics', 'content': {'items': value}}
        bullets = []
        for item in value:
            if isinstance(item, (str, int, float, bool)) or item is None:
                bullets.append(str(item))
            else:
                bullets.append(json.dumps(item, ensure_ascii=True))
        return {'type': 'descriptive', 'content': {'bullets': bullets}}

    return {'type': 'descriptive', 'content': {'text': [str(value)]}}


def _normalize_input_payload(payload):
    """Convert raw input into the expected {data: {section: {type, content}}} shape."""
    if not isinstance(payload, dict):
        return {'data': {'input': _normalize_section_value(payload)}}

    if isinstance(payload.get('data'), dict):
        data = payload['data']
    else:
        data = {k: v for k, v in payload.items() if k != 'client_name'}

    normalized = {key: _normalize_section_value(value) for key, value in data.items()}
    result = {'data': normalized}
    if 'client_name' in payload:
        result['client_name'] = payload.get('client_name')
    return result


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

        # Normalize input so arrays/values do not fail schema validation.
        input_data = _normalize_input_payload(input_data)

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
