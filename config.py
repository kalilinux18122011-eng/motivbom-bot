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
GROK_ACCESS_TOKEN = os.getenv("GROK_ACCESS_TOKEN", "").strip()
GROK_REFRESH_TOKEN = os.getenv("GROK_REFRESH_TOKEN", "").strip()
GROK_CLIENT_ID = os.getenv("GROK_CLIENT_ID", "").strip()
GROK_EXPIRES_AT = os.getenv("GROK_EXPIRES_AT", "").strip()
XAI_BASE = "https://api.x.ai/v1"
LLM_MODEL = os.getenv("LLM_MODEL", "grok-4.7").strip()
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "grok-imagine-image-2.0").strip()
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "grok-imagine-video-1.5").strip()
IG_USERNAME = os.getenv("IG_USERNAME", "motivbom").strip()
IG_PASSWORD = os.getenv("IG_PASSWORD", "").strip()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "").strip()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://motivbom-bot.onrender.com").rstrip("/")
MAX_ANALYSIS_VIDEO_MB = max(1, int(os.getenv("MAX_ANALYSIS_VIDEO_MB", "40")))
AUTO_POST = os.getenv("AUTO_POST", "1").lower() not in {"0", "false", "no"}
# The production cadence is expressed only in minutes. Do not fall back to the
# retired POST_INTERVAL_HOURS variable: existing Render services preserve old
# environment variables after render.yaml changes.
POST_INTERVAL_MINUTES = max(
    1,
    int(os.getenv("POST_INTERVAL_MINUTES", "30")),
)


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
