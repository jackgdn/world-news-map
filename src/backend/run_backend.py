try:
    from . import config
    from .fetch_coord import refresh_weekly_coordinates
    from .fetch_news import refresh_weekly_news
    from .fetch_poi import refresh_weekly_poi
    from .utils import logger
except ImportError:
    import config
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
        logger.info(
            f"Next scheduled refresh in {config.UPDATE_INTERVAL_HOURS} hours.")
    except Exception as e:
        logger.error(f"Error during full data refresh: {e}", exc_info=True)
        raise



if __name__ == "__main__":
    refresh_all_data()