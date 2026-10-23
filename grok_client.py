from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import httpx

import config


class GrokError(RuntimeError):
    pass


_oauth_token = config.GROK_ACCESS_TOKEN
_oauth_expires_at = config.GROK_EXPIRES_AT


def _expiry(raw: str) -> float:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _refresh_oauth() -> str:
    global _oauth_token, _oauth_expires_at
    if not config.GROK_REFRESH_TOKEN or not config.GROK_CLIENT_ID:
        return _oauth_token
    body = urlencode({"grant_type": "refresh_token", "refresh_token": config.GROK_REFRESH_TOKEN, "client_id": config.GROK_CLIENT_ID}).encode()
    request = Request("https://auth.x.ai/oauth2/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    _oauth_token = str(payload.get("access_token") or "")
    expires_in = int(payload.get("expires_in") or 7200)
    _oauth_expires_at = datetime.fromtimestamp(time.time() + expires_in, timezone.utc).isoformat()
    return _oauth_token


def _bearer_token() -> str:
    # xAI has issued both legacy ``xai-`` keys and current ``grok_`` keys.
    # Do not confuse either developer-key format with a browser OAuth token.
    if config.XAI_API_KEY.startswith(("xai-", "grok_")):
        return config.XAI_API_KEY
    if _oauth_token and _expiry(_oauth_expires_at) - time.time() > 90:
        return _oauth_token
    try:
        return _refresh_oauth()
    except Exception as exc:
        raise GrokError(f"Grok OAuth token yangilanmadi: {exc}") from exc


def _headers() -> dict[str, str]:
    token = _bearer_token()
    if not token:
        raise GrokError("Grok OAuth yoki XAI_API_KEY sozlanmagan")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def image_data(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


async def chat(messages: list[dict], *, max_tokens: int = 1800) -> str:
    body = {"model": config.LLM_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": max_tokens}
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{config.XAI_BASE}/chat/completions", headers=_headers(), json=body)
    if response.status_code >= 400:
        raise GrokError(f"Grok chat {response.status_code}: {response.text[:500]}")
    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise GrokError("Grok вернул ответ без текста") from exc


def json_object(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise GrokError("Grok не вернул JSON")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise GrokError(f"Некорректный JSON от Grok: {text[:300]}") from exc
    if not isinstance(value, dict):
        raise GrokError("Ожидался JSON-объект")
    return value


async def generate_image(prompt: str, destination: Path) -> Path:
    body = {"model": config.IMAGE_MODEL, "prompt": prompt, "aspect_ratio": "9:16", "resolution": "1k"}
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{config.XAI_BASE}/images/generations", headers=_headers(), json=body)
        if response.status_code >= 400:
            raise GrokError(f"Grok image {response.status_code}: {response.text[:500]}")
        url = response.json()["data"][0]["url"]
        image = await client.get(url, timeout=180)
        image.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image.content)
    return destination


async def generate_video(prompt: str, destination: Path, reference: Path) -> Path:
    body = {"model": config.VIDEO_MODEL, "prompt": prompt, "duration": 15, "aspect_ratio": "9:16", "resolution": "720p", "reference_images": [{"url": image_data(reference)}]}
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{config.XAI_BASE}/videos/generations", headers=_headers(), json=body)
        if response.status_code >= 400:
            raise GrokError(f"Grok video {response.status_code}: {response.text[:500]}")
        request_id = response.json().get("request_id")
        if not request_id:
            raise GrokError("Grok video не вернул request_id")
        for _ in range(120):
            await asyncio.sleep(5)
            status = await client.get(f"{config.XAI_BASE}/videos/{request_id}", headers=_headers())
            if status.status_code >= 400:
                raise GrokError(f"Grok video status {status.status_code}: {status.text[:300]}")
            data = status.json()
            if data.get("status") == "done":
                url = (data.get("video") or {}).get("url")
                if not url:
                    raise GrokError("Видео готово, но URL отсутствует")
                video = await client.get(url, timeout=180)
                video.raise_for_status()
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(video.content)
                return destination
            if data.get("status") in {"failed", "expired"}:
                raise GrokError(f"Grok video {data.get('status')}: {data}")
    raise GrokError("Grok не сгенерировал видео за 10 минут")
