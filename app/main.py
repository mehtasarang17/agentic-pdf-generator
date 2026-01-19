"""Main entry point for the Agentic PDF Generator application."""

from app import create_app
from app.config import config

app = create_app()

if __name__ == "__main__":
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )
