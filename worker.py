import time
import schedule
import logging
from pipeline import MotivBomPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Worker")

pipeline = MotivBomPipeline()

def job():
    logger.info("Starting scheduled Reel creation and posting cycle for @motivbom...")
    try:
        script = pipeline.generate_script()
        video_path = pipeline.prepare_video(script)
        pipeline.publish_to_instagram(video_path, script)
        logger.info("Cycle completed successfully.")
    except Exception as e:
        logger.error(f"Error in publishing cycle: {e}")

# Schedule 6 posts per day with 30-minute advance preparation
# e.g., prepare at 21:30 for posting at 22:00
schedule.every(4).hours.do(job)

if __name__ == "__main__":
    logger.info("Worker scheduler started for @motivbom (motivbom_bot). Press Ctrl+C to exit.")
    # Run once immediately for testing if needed
    # job()

    while True:
        schedule.run_pending()
        time.sleep(60)
