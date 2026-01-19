"""Agentic PDF Generator - A multi-agent system for generating professional PDFs."""

import time
import logging
from flask import Flask
from flask_cors import CORS

from app.config import config
from app.models.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_db(app, max_retries=30, delay=2):
    """Wait for database to be ready with retries."""
    for attempt in range(max_retries):
        try:
            with app.app_context():
                db.create_all()
                logger.info("Database connection established and tables created.")
                return True
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    logger.error("Could not connect to database after maximum retries")
    return False


def create_app():
    """Application factory for creating the Flask app."""
    app = Flask(__name__)

    # Configure CORS
    CORS(app)

    # Load configuration
    app.config.from_object(config)

    # Initialize database
    db.init_app(app)

    # Wait for database and create tables
    wait_for_db(app)

    # Register blueprints
    from app.routes.pdf_routes import pdf_bp
    app.register_blueprint(pdf_bp, url_prefix="/api/v1")

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return {"status": "healthy", "service": "agentic-pdf-generator"}

    return app
