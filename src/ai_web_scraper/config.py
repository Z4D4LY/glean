"""Configuration loaded lazily to avoid import-time side effects."""

import os
from pathlib import Path


def load_config():
    return {
        "base_url": os.getenv("API_BASE_URL", "http://localhost:11434/v1"),
        "model": os.getenv("MODEL", "qwen2.5:14b"),
        "api_key": os.getenv("API_KEY", "ollama"),
        "temperature": float(os.getenv("TEMPERATURE", "0.6")),
    }


def load_settings():
    return {
        "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
        "max_content_length": int(os.getenv("MAX_CONTENT_LENGTH", "1000000")),
    }


def get_save_dir() -> Path:
    return Path(
        os.getenv("SAVE_DIR", str(Path.home() / ".ai-web-scraper" / "scraped"))
    ).expanduser()
