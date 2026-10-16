from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

import config
from grok_client import GrokError, chat, generate_image, generate_video, image_data, json_object
from instagram import post_reel

logger = logging.getLogger(__name__)
SHAKER = "one black matte 3D protein shaker with a friendly expressive face and muscular human arms"
NUTRITION_SOURCES = {
    "kreatin": "https://ods.od.nih.gov/factsheets/ExerciseAndAthleticPerformance-HealthProfessional/",
    "protein": "https://www.ncbi.nlm.nih.gov/books/NBK278935/",
    "magniy": "https://ods.od.nih.gov/factsheets/Magnesium-HealthProfessional/",
    "omega-3": "https://ods.od.nih.gov/factsheets/Omega3FattyAcids-HealthProfessional/",
    "kofein": "https://ods.od.nih.gov/factsheets/ExerciseAndAthleticPerformance-HealthProfessional/",
}


class MotivBomPipeline:
    def __init__(self) -> None:
        config.ensure_dirs()
        self.history_file = config.DATA_DIR / "published.jsonl"

    def notify(self, text: str) -> None:
        if not config.TG_BOT_TOKEN or not config.TG_CHAT_ID:
            logger.warning("Telegram notification skipped: credentials are not configured")
            return
        try:
            requests.post(f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage", json={"chat_id": config.TG_CHAT_ID, "text": text[:4000]}, timeout=20).raise_for_status()
        except requests.RequestException:
            logger.exception("Telegram notification failed")

    def _recent_topics(self) -> str:
        if not self.history_file.exists():
            return "yo'q"
        lines = self.history_file.read_text(encoding="utf-8").splitlines()[-20:]
        return "\n".join(json.loads(line).get("idea", "") for line in lines if line) or "yo'q"

    async def propose_idea(self) -> dict:
        raw = await chat([{"role": "system", "content": "Sen @motivbom uchun kontent-strategsan. Faqat JSON qaytar. Tibbiy tashxis, davolash va kafolatlangan natija va'da qilma."}, {"role": "user", "content": f"O'zbekistondagi sport bilan shug'ullanuvchilar uchun yangi Reel g'oyasi top. Mavzu sport ovqati: kreatin, protein, magniy, omega-3, kofein yoki ovqatlanish. Qahramon: {SHAKER}. Oxirgi g'oyalarni takrorlama:\n{self._recent_topics()}\nJSON: {{\"idea\":\"...\",\"product\":\"...\",\"audience_problem\":\"...\",\"angle\":\"...\"}}"}], max_tokens=700)
        idea = json_object(raw)
        if not idea.get("idea") or not idea.get("product"):
            raise GrokError("Idea agent yetarli ma'lumot qaytarmadi")
        return idea

    async def create_script(self, idea: dict) -> dict:
        raw = await chat([{"role": "system", "content": "Sen o'zbekcha Instagram Reels ssenariychi va videoprompt muallifisan. Faqat JSON qaytar. Lotin o'zbek tilida yoz. Tibbiy va'da, xavfli doza, steroid reklamasini qilma."}, {"role": "user", "content": f"G'oya: {json.dumps(idea, ensure_ascii=False)}. 18-20 sekundlik vertikal 9:16 Reel yoz. Qahramon doim {SHAKER}; boshqa odamlar yo'q. Birinchi 2 sekundda kuchli hook bo'lsin. JSON: {{\"spoken\":\"18-20 sekund o'zbekcha nutq\",\"caption\":\"qisqa caption va 4-7 hashtag\",\"video_prompt\":\"English cinematic 9:16 visual prompt, include exact shaker identity, Uzbek spoken words, no subtitles, no logos, no watermark\"}}"}], max_tokens=1200)
        script = json_object(raw)
        if not all(script.get(k) for k in ("spoken", "caption", "video_prompt")):
            raise GrokError("Creator agent ssenariyni to'liq qaytarmadi")
        return script

    def sources_for(self, idea: dict) -> list[str]:
        product = str(idea.get("product", "")).lower()
        sources = [url for word, url in NUTRITION_SOURCES.items() if word in product]
        return sources or ["https://ods.od.nih.gov/factsheets/ExerciseAndAthleticPerformance-HealthProfessional/"]

    async def shaker_reference(self) -> Path:
        if config.CHARACTER_FILE.exists() and config.CHARACTER_FILE.stat().st_size > 1000:
            return config.CHARACTER_FILE
        if config.CHARACTER_SOURCE.exists():
            shutil.copy2(config.CHARACTER_SOURCE, config.CHARACTER_FILE)
            return config.CHARACTER_FILE
        return await generate_image("Studio character reference, full-body vertical 9:16. A single black matte 3D protein shaker bottle with a friendly expressive face, muscular human arms, wearing no clothes, clean dark gym background. Premium Pixar-like product animation, no text, no logos, no watermark.", config.CHARACTER_FILE)

    def _video_facts(self, video: Path) -> dict:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", str(video)], check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        stream = next((s for s in data.get("streams", []) if s.get("width")), {})
        return {"duration": round(float(data["format"]["duration"]), 2), "width": stream.get("width"), "height": stream.get("height")}

    def _frames(self, video: Path) -> list[Path]:
        frames = []
        for second in (1, 7, 14):
            destination = config.DATA_DIR / f"review_{second}.jpg"
            subprocess.run(["ffmpeg", "-y", "-ss", str(second), "-i", str(video), "-frames:v", "1", "-q:v", "3", str(destination)], check=True, capture_output=True)
            frames.append(destination)
        return frames

    async def critique(self, video: Path, idea: dict, script: dict) -> dict:
        facts = self._video_facts(video)
        if facts["height"] <= facts["width"] or not 15 <= facts["duration"] <= 25:
            return {"approved": False, "score": 0, "reason": f"Texnik xato: {facts}"}
        content: list[dict] = [{"type": "text", "text": f"Sen qattiqqo'l Reel kritiksan. G'oya: {idea['idea']}. Ssenariy: {script['spoken']}. Kadrlarni bahola: qahramon bir xil qora 3D shakerligini, vertikal formatni, birinchi kadr hookini, artefakt/watermark yo'qligini va brend xavfsizligini tekshir. Faqat JSON: {{\"approved\":true/false,\"score\":0-100,\"reason\":\"qisqa\"}}"}]
        content.extend({"type": "image_url", "image_url": {"url": image_data(frame)}} for frame in self._frames(video))
        raw = await chat([{"role": "system", "content": "Faqat JSON qaytar."}, {"role": "user", "content": content}], max_tokens=500)
        result = json_object(raw)
        result["approved"] = bool(result.get("approved")) and int(result.get("score", 0)) >= 75
        return result

    def _record(self, record: dict) -> None:
        with self.history_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def run_once(self) -> None:
        idea = await self.propose_idea()
        self.notify(f"💡 @motivbom idea: {idea['idea']}\nYaratish boshlandi.")
        script = await self.create_script(idea)
        reference = await self.shaker_reference()
        video = config.VIDEO_DIR / f"reel_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp4"
        await generate_video(script["video_prompt"], video, reference)
        review = await self.critique(video, idea, script)
        if not review.get("approved"):
            self.notify(f"⚠️ @motivbom video kritikdan o'tmadi ({review.get('score', 0)}/100): {review.get('reason', '')}. Post qilinmadi.")
            return
        if not config.AUTO_POST:
            self.notify(f"✅ @motivbom video tasdiqlandi ({review.get('score')}/100), AUTO_POST=0: post qilinmadi.")
            return
        media_id = await asyncio.to_thread(post_reel, video, script["caption"])
        self._record({"at": datetime.now(timezone.utc).isoformat(), "idea": idea["idea"], "media_id": media_id, "caption": script["caption"], "review": review, "sources": self.sources_for(idea)})
        self.notify(f"🚀 @motivbom Instagramga chiqdi!\nID: {media_id}\nBahosi: {review.get('score')}/100\n{idea['idea']}\nhttps://www.instagram.com/{config.IG_USERNAME}/")
