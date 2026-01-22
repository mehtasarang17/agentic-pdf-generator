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
    LLM_INPUT_TOKEN_BUDGET = int(os.getenv("LLM_INPUT_TOKEN_BUDGET", "120000"))
    LLM_CHUNK_TOKEN_BUDGET = int(os.getenv("LLM_CHUNK_TOKEN_BUDGET", "20000"))
    LLM_MERGE_TOKEN_BUDGET = int(os.getenv("LLM_MERGE_TOKEN_BUDGET", "8000"))
    LLM_DIGEST_TOKEN_BUDGET = int(os.getenv("LLM_DIGEST_TOKEN_BUDGET", "8000"))
    LLM_MAX_CHUNK_CALLS = int(os.getenv("LLM_MAX_CHUNK_CALLS", "40"))
    LLM_STRUCTURED_BASE_PARAGRAPHS = os.getenv(
        "LLM_STRUCTURED_BASE_PARAGRAPHS",
        "2-3"
    )
    LLM_STRUCTURED_BASE_BULLETS = os.getenv(
        "LLM_STRUCTURED_BASE_BULLETS",
        "3-7"
    )
    LLM_STRUCTURED_BASE_FINDINGS = os.getenv(
        "LLM_STRUCTURED_BASE_FINDINGS",
        "2-5"
    )
    LLM_STRUCTURED_DETAIL_PARAGRAPHS = os.getenv(
        "LLM_STRUCTURED_DETAIL_PARAGRAPHS",
        "4-6"
    )
    LLM_STRUCTURED_DETAIL_BULLETS = os.getenv(
        "LLM_STRUCTURED_DETAIL_BULLETS",
        "7-12"
    )
    LLM_STRUCTURED_DETAIL_FINDINGS = os.getenv(
        "LLM_STRUCTURED_DETAIL_FINDINGS",
        "4-7"
    )
    LLM_STRUCTURED_MAX_TOKENS = int(os.getenv("LLM_STRUCTURED_MAX_TOKENS", "1500"))
    LLM_STRUCTURED_MAX_TOKENS_DETAIL = int(
        os.getenv("LLM_STRUCTURED_MAX_TOKENS_DETAIL", "2200")
    )
    LLM_TABLE_VALUE_TOKEN_BUDGET = int(os.getenv("LLM_TABLE_VALUE_TOKEN_BUDGET", "12000"))
    LLM_TABLE_VALUE_MAX_TOKENS = int(os.getenv("LLM_TABLE_VALUE_MAX_TOKENS", "1200"))
    LLM_TABLE_VALUE_REWRITE_MAX = int(os.getenv("LLM_TABLE_VALUE_REWRITE_MAX", "15"))
    LLM_TABLE_VALUE_REWRITE_MAX_TOKENS = int(
        os.getenv("LLM_TABLE_VALUE_REWRITE_MAX_TOKENS", "400")
    )

    ANALYTICS_NUMERIC_RATIO = float(os.getenv("ANALYTICS_NUMERIC_RATIO", "0.3"))
    ANALYTICS_MIN_NUMERIC_VALUES = int(os.getenv("ANALYTICS_MIN_NUMERIC_VALUES", "4"))
    ANALYTICS_SERIES_MIN_LENGTH = int(os.getenv("ANALYTICS_SERIES_MIN_LENGTH", "3"))
    ANALYTICS_SAMPLE_LIMIT = int(os.getenv("ANALYTICS_SAMPLE_LIMIT", "5000"))

    VISUALIZER_MAX_CATEGORIES = int(os.getenv("VISUALIZER_MAX_CATEGORIES", "12"))
    VISUALIZER_MAX_SERIES_ITEMS = int(os.getenv("VISUALIZER_MAX_SERIES_ITEMS", "30"))
    LLM_TOKEN_ESTIMATE_CHARS_PER_TOKEN = float(
        os.getenv("LLM_TOKEN_ESTIMATE_CHARS_PER_TOKEN", "4.0")
    )
    LLM_MAX_FIELD_CHARS = int(os.getenv("LLM_MAX_FIELD_CHARS", "8000"))

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
