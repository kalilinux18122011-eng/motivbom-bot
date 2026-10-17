from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl
from datetime import datetime, timezone

from aiohttp import web

import config
from aiohttp import web
from content_agents import analyst, director, scriptwriter
from pipeline import MotivBomPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def health(_request: web.Request) -> web.Response:
    app = _request.app
    return web.json_response({
        "ok": True,
        "account": config.IG_USERNAME,
        "auto_post": config.AUTO_POST,
        "interval_minutes": config.POST_INTERVAL_MINUTES,
        "cycle": app.get("cycle", {"state": "starting"}),
    })


def valid_telegram_init_data(raw: str) -> bool:
    """Telegram signs Mini App initData; never trust browser-provided user data alone."""
    if not raw or not config.TG_BOT_TOKEN:
        return False
    values = dict(parse_qsl(raw, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        return False
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", config.TG_BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_hash)


async def mini_app(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path(__file__).with_name("static") / "miniapp.html")


async def run_agent(request: web.Request) -> web.Response:
    if not valid_telegram_init_data((await request.post()).get("init_data", "")):
        return web.json_response({"error": "Открой Mini App именно из Telegram."}, status=401)
    # request.post() is cached by aiohttp, so uploaded video remains accessible.
    form = await request.post()
    agent = request.match_info["agent"]
    payload = {key: str(form.get(key, "")).strip() for key in ("context", "views", "likes", "comments", "shares", "saves", "notes")}
    try:
        if agent == "analyst":
            video_path = None
            uploaded = form.get("video")
            if getattr(uploaded, "file", None):
                raw = uploaded.file.read()
                if len(raw) > config.MAX_ANALYSIS_VIDEO_MB * 1024 * 1024:
                    return web.json_response({"error": f"Видео больше {config.MAX_ANALYSIS_VIDEO_MB} МБ."}, status=413)
                suffix = Path(getattr(uploaded, "filename", "video.mp4")).suffix or ".mp4"
                video_path = config.DATA_DIR / "analysis_uploads" / f"upload_{os.urandom(8).hex()}{suffix}"
                video_path.parent.mkdir(parents=True, exist_ok=True)
                video_path.write_bytes(raw)
            answer = await analyst(payload, video_path)
        elif agent == "scriptwriter":
            answer = await scriptwriter(payload)
        elif agent == "director":
            answer = await director(payload)
        else:
            return web.json_response({"error": "Неизвестный агент."}, status=404)
    except Exception as exc:
        logger.exception("Content agent failed: %s", agent)
        return web.json_response({"error": f"Агент не смог закончить: {type(exc).__name__}"}, status=502)
    return web.json_response({"answer": answer})


async def configure_telegram_menu() -> None:
    """Make the Mini App available from the bot's menu without exposing the token."""
    if not config.TG_BOT_TOKEN:
        return
    import requests
    try:
        await asyncio.to_thread(requests.post, f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/setChatMenuButton", json={"menu_button": {"type": "web_app", "text": "MotivBom Studio", "web_app": {"url": config.MINI_APP_URL}}}, timeout=20)
    except Exception:
        logger.exception("Could not configure Telegram Mini App menu")


async def poster_loop(app: web.Application) -> None:
    pipeline = MotivBomPipeline()
    await asyncio.sleep(20)
    while True:
        app["cycle"] = {"state": "running", "started_at": datetime.now(timezone.utc).isoformat()}
        try:
            await pipeline.run_once()
            app["cycle"] = {"state": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
        except Exception as exc:
            logger.exception("@motivbom cycle failed")
            app["cycle"] = {"state": "failed", "failed_at": datetime.now(timezone.utc).isoformat(), "error": f"{type(exc).__name__}: {exc}"[:1000]}
            pipeline.notify(f"❌ @motivbom agent xatosi: {type(exc).__name__}: {exc}")
        await asyncio.sleep(config.POST_INTERVAL_MINUTES * 60)


async def on_startup(app: web.Application) -> None:
    app["cycle"] = {"state": "starting"}
    app["poster_task"] = asyncio.create_task(poster_loop(app))
    app["menu_task"] = asyncio.create_task(configure_telegram_menu())


async def on_cleanup(app: web.Application) -> None:
    task = app.get("poster_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def make_app() -> web.Application:
    app = web.Application(client_max_size=(config.MAX_ANALYSIS_VIDEO_MB + 2) * 1024 * 1024)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/miniapp", mini_app)
    app.router.add_post("/api/agents/{agent}", run_agent)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
