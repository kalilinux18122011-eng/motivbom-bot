from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web

import config
from pipeline import MotivBomPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "account": config.IG_USERNAME, "auto_post": config.AUTO_POST})


async def poster_loop(app: web.Application) -> None:
    pipeline = MotivBomPipeline()
    await asyncio.sleep(20)
    while True:
        try:
            await pipeline.run_once()
        except Exception as exc:
            logger.exception("@motivbom cycle failed")
            pipeline.notify(f"❌ @motivbom agent xatosi: {type(exc).__name__}: {exc}")
        await asyncio.sleep(config.POST_INTERVAL_MINUTES * 60)


async def on_startup(app: web.Application) -> None:
    app["poster_task"] = asyncio.create_task(poster_loop(app))


async def on_cleanup(app: web.Application) -> None:
    task = app.get("poster_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
