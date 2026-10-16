from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
VIDEO_DIR = DATA_DIR / "videos"
SESSION_FILE = DATA_DIR / "ig_session.json"
CHARACTER_FILE = DATA_DIR / "shaker.jpg"
CHARACTER_SOURCE = BASE_DIR / "assets" / "shaker.jpg"
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
XAI_BASE = "https://api.x.ai/v1"
LLM_MODEL = os.getenv("LLM_MODEL", "grok-4.7").strip()
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "grok-imagine-image-2.0").strip()
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "grok-imagine-video-1.5").strip()
IG_USERNAME = os.getenv("IG_USERNAME", "motivbom").strip()
IG_PASSWORD = os.getenv("IG_PASSWORD", "").strip()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "").strip()
AUTO_POST = os.getenv("AUTO_POST", "1").lower() not in {"0", "false", "no"}
POST_INTERVAL_HOURS = max(1, int(os.getenv("POST_INTERVAL_HOURS", "6")))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
