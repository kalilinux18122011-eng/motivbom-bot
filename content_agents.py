from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from pathlib import Path

import config
from grok_client import analyze_frames, chat


def _record(kind: str, payload: dict, answer: str) -> None:
    config.ensure_dirs()
    path = config.DATA_DIR / "content_agent_history.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"kind": kind, "payload": payload, "answer": answer}, ensure_ascii=False) + "\n")


async def extract_frames(video: Path) -> list[Path]:
    folder = config.DATA_DIR / "analysis" / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "frame-%02d.jpg"
    command = ["ffmpeg", "-y", "-i", str(video), "-vf", "select='eq(n,0)+gt(scene,0.28)',scale=360:-2", "-frames:v", "4", str(output)]
    result = await asyncio.to_thread(subprocess.run, command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    frames = sorted(folder.glob("frame-*.jpg"))
    if result.returncode or not frames:
        raise RuntimeError("Не удалось извлечь кадры из видео. Загрузите обычный MP4-файл.")
    return frames


async def analyst(payload: dict, video: Path | None = None) -> str:
    stats = "\n".join(f"- {key}: {value}" for key, value in payload.items() if value and key != "notes") or "метрики не переданы"
    task = f"""Разбери Reel аккаунта @motivbom.ai для улучшения следующих публикаций.
Реальные метрики: {stats}
Комментарий автора: {payload.get('notes', 'нет')}
Дай отчёт на русском: 1) что видно и работает/не работает, 2) 3 конкретных косяка, 3) что проверить в первых 2 секундах, 4) какие метрики сравнить с другими роликами. Не заявляй, что формат набирает больше просмотров без нескольких роликов и их цифр."""
    if video:
        frames = await extract_frames(video)
        answer = await analyze_frames(task, frames)
    else:
        answer = await chat([{"role": "user", "content": task + "\nВидео не приложено, поэтому оцени только метрики и пометь ограничения."}])
    _record("analyst", payload, answer)
    return answer


async def scriptwriter(payload: dict) -> str:
    report = payload.get("context", "")
    task = f"""Ты сценарист Reels для @motivbom.ai — спортпит на узбекском (латиница).
Вот отчёт аналитика или задача пользователя:\n{report}
Сделай 3 разных сценария по 15–20 секунд. Для каждого: Hook 0–2с, кадры по секундам, текст озвучки на узбекском, CTA, caption. Никаких медицинских обещаний, дозировок без источника и повторов."""
    answer = await chat([{"role": "user", "content": task}], max_tokens=2200)
    _record("scriptwriter", payload, answer)
    return answer


async def director(payload: dict) -> str:
    context = payload.get("context", "")
    task = f"""Ты контент-директор @motivbom.ai. Получил материал ниже:\n{context}
Улучши его перед публикацией. Верни: 1) один лучший вариант и почему, 2) сильный первый кадр/обложка, 3) точный CTA, 4) подпись и 5–7 релевантных хэштегов, 5) A/B тест — что изменить в двух версиях, 6) таблицу метрик, которые надо записать через 24 часа. Не выдумывай тренды и не обещай охваты."""
    answer = await chat([{"role": "user", "content": task}], max_tokens=2200)
    _record("director", payload, answer)
    return answer
