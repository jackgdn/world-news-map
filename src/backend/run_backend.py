import config
import schedule
import time
from fetch_coord import refresh_weekly_coordinates
from fetch_news import refresh_weekly_news
from fetch_poi import refresh_weekly_poi
from utils import logger


def refresh_all_data() -> None:
    try:
        logger.info("Starting full data refresh task...")
        refresh_weekly_news()
        refresh_weekly_poi()
        refresh_weekly_coordinates()
        logger.info("Full data refresh task completed successfully.")
    except Exception as e:
        logger.error(f"Error during full data refresh: {e}", exc_info=True)
        raise


def run_backend() -> None:
    refresh_all_data()
    update_interval = config.UPDATE_INTERVAL_HOURS
    schedule.every(update_interval).hours.do(refresh_all_data)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user, stopping backend gracefully...")
    except Exception as e:
        logger.error(f"Unexpected error in backend: {e}", exc_info=True)
        raise
    finally:
        logger.info("Backend stopped, clearing scheduled tasks...")
        schedule.clear()


if __name__ == "__main__":
    run_backend()
