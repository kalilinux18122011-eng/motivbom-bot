from __future__ import annotations

from pathlib import Path

from instagrapi import Client

import config


class InstagramError(RuntimeError):
    pass


def post_reel(video: Path, caption: str) -> str:
    if not video.exists():
        raise InstagramError(f"Видео не найдено: {video}")
    if not config.IG_USERNAME or not config.IG_PASSWORD:
        raise InstagramError("Не заданы IG_USERNAME/IG_PASSWORD")
    config.ensure_dirs()
    client = Client()
    client.delay_range = [1, 3]
    if config.SESSION_FILE.exists():
        client.load_settings(config.SESSION_FILE)
    client.login(config.IG_USERNAME, config.IG_PASSWORD)
    client.dump_settings(config.SESSION_FILE)
    media = client.clip_upload(str(video), caption=caption)
    return str(getattr(media, "id", None) or getattr(media, "pk", None) or media)
