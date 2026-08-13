"""Configuration helpers."""

import os
from pathlib import Path


def _env_float(key: str, default: str) -> float:
    try:
        return float(os.getenv(key, default))
    except (ValueError, TypeError):
        return float(default)


def _env_int(key: str, default: str) -> int:
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return int(default)


def load_config():
    return {
        "base_url": os.getenv("API_BASE_URL", "http://localhost:11434/v1"),
        "model": os.getenv("MODEL", "qwen2.5:14b"),
        "api_key": os.getenv("API_KEY", "ollama"),
        "temperature": _env_float("TEMPERATURE", "0.6"),
        "api_timeout": _env_float("API_TIMEOUT", "60"),
    }


def load_settings():
    return {
        "request_timeout": _env_int("REQUEST_TIMEOUT", "30"),
        "max_content_length": _env_int("MAX_CONTENT_LENGTH", "1000000"),
    }


def get_save_dir() -> Path:
    return Path(
        os.getenv("SAVE_DIR", str(Path.home() / ".glean" / "scraped"))
    ).expanduser()
