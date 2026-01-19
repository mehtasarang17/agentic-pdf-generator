from datetime import datetime
from app.models.database import db


class PDFDocument(db.Model):
    """Model for storing PDF document metadata."""

    __tablename__ = 'pdf_documents'

    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500))

    # Metadata
    pages = db.Column(db.Integer)
    file_size = db.Column(db.BigInteger)
    sections = db.Column(db.JSON)

    # Input data stored for reference
    input_data = db.Column(db.JSON)

    # Status tracking
    status = db.Column(db.String(50), default='completed')
    error_message = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'filename': self.filename,
            'client_name': self.client_name,
            'title': self.title,
            'pages': self.pages,
            'size': self.file_size,
            'sections': self.sections,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'download_url': f'/api/v1/download/{self.id}'
        }

    def __repr__(self):
        return f'<PDFDocument {self.id}: {self.filename}>'
