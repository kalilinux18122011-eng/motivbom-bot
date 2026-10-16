# @motivbom autonomous Reels agent

The agent runs four stages: an idea agent chooses a new sport-nutrition topic; a creator writes Uzbek script and creates a 15-second Grok Reel; a critic inspects three extracted frames and technical video facts; the publisher uploads only approved videos to Instagram and notifies Telegram.

Set the variables from `.env.example` in Render. `XAI_API_KEY` is required because a local Grok login session cannot be used from Render. `AUTO_POST=0` keeps the full pipeline but stops before Instagram publishing. The approved shaker reference is bundled in `assets/shaker.jpg`, so its appearance stays consistent across videos.

`/health` reports whether the service is live. Each accepted post is recorded in `data/published.jsonl`; files on Render free instances are ephemeral.
