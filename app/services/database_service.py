import os
from typing import Optional, List
from app.models.database import db
from app.models.pdf import PDFDocument


class DatabaseService:
    """Service for database operations on PDF documents."""

    @staticmethod
    def create_pdf_record(
        pdf_id: str,
        filename: str,
        client_name: str,
        title: Optional[str] = None,
        pages: Optional[int] = None,
        file_size: Optional[int] = None,
        sections: Optional[List[str]] = None,
        input_data: Optional[dict] = None,
        status: str = 'completed'
    ) -> PDFDocument:
        """Create a new PDF document record."""
        pdf_doc = PDFDocument(
            id=pdf_id,
            filename=filename,
            client_name=client_name,
            title=title,
            pages=pages,
            file_size=file_size,
            sections=sections,
            input_data=input_data,
            status=status
        )
        db.session.add(pdf_doc)
        db.session.commit()
        return pdf_doc

    @staticmethod
    def get_pdf_by_id(pdf_id: str) -> Optional[PDFDocument]:
        """Get a PDF document by ID."""
        return PDFDocument.query.get(pdf_id)

    @staticmethod
    def get_all_pdfs(limit: int = 100, offset: int = 0) -> List[PDFDocument]:
        """Get all PDF documents with pagination."""
        return PDFDocument.query.order_by(
            PDFDocument.created_at.desc()
        ).offset(offset).limit(limit).all()

    @staticmethod
    def delete_pdf(pdf_id: str) -> bool:
        """Delete a PDF document record."""
        pdf_doc = PDFDocument.query.get(pdf_id)
        if pdf_doc:
            db.session.delete(pdf_doc)
            db.session.commit()
            return True
        return False

    @staticmethod
    def update_pdf_status(pdf_id: str, status: str, error_message: Optional[str] = None) -> Optional[PDFDocument]:
        """Update PDF document status."""
        pdf_doc = PDFDocument.query.get(pdf_id)
        if pdf_doc:
            pdf_doc.status = status
            if error_message:
                pdf_doc.error_message = error_message
            db.session.commit()
        return pdf_doc

    @staticmethod
    def get_pdfs_by_client(client_name: str) -> List[PDFDocument]:
        """Get all PDFs for a specific client."""
        return PDFDocument.query.filter_by(
            client_name=client_name
        ).order_by(PDFDocument.created_at.desc()).all()

    @staticmethod
    def update_file_size(pdf_id: str, file_path: str) -> Optional[PDFDocument]:
        """Update the file size of a PDF document."""
        pdf_doc = PDFDocument.query.get(pdf_id)
        if pdf_doc and os.path.exists(file_path):
            pdf_doc.file_size = os.path.getsize(file_path)
            db.session.commit()
        return pdf_doc
