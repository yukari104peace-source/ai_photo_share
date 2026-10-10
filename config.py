import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


def load_config():
    root = Path(__file__).resolve().parent
    load_dotenv(root / ".env")
    return {
        "POST_UPLOAD_DIR": root / "uploads" / "posts",
        "MAX_IMAGE_BYTES": 5 * 1024 * 1024,
        "MAX_CONTENT_LENGTH": 6 * 1024 * 1024,
        "ALLOWED_IMAGE_EXTENSIONS": {"png", "jpg", "jpeg", "gif"},
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "DATABASE": root / "instance" / "app.sqlite3",
        "SESSION_TYPE": "cachelib",
        "SESSION_CACHE_DIR": root / "instance" / "sessions",
        "SESSION_PERMANENT": False,
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=12),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.environ.get("SESSION_COOKIE_SECURE") == "1",
    }
