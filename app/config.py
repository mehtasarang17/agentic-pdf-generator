"""Configuration settings for the Agentic PDF Generator."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Flask settings
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "8500"))

    # Database settings
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://pdfuser:pdfpassword@localhost:5432/pdfgenerator"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # PDF settings
    BASE_DIR = Path(__file__).parent.parent
    PDF_OUTPUT_DIR = BASE_DIR / os.getenv("PDF_OUTPUT_DIR", "generated_pdfs")
    ASSETS_DIR = Path(__file__).parent / "assets"
    LOGO_PATH = ASSETS_DIR / "infopercept_logo.png"
    WATERMARK_PATH = ASSETS_DIR / os.getenv(
        "WATERMARK_PATH",
        "infopercept_watermark.png"
    )
    WATERMARK_OPACITY = float(os.getenv("WATERMARK_OPACITY", "0.15"))

    MIN_PAGES = int(os.getenv("MIN_PAGES", "7"))
    MAX_PAGES = int(os.getenv("MAX_PAGES", "100"))

    # Ensure directories exist
    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
