try:
    from . import config
    from .fetch_coord import refresh_weekly_coordinates
    from .fetch_news import refresh_weekly_news
    from .fetch_poi import refresh_weekly_poi
    from .generate_metadata import (generate_robots_txt, generate_security_txt,
                                    generate_sitemap)
    from .utils import logger
except ImportError:
    import config
    from fetch_coord import refresh_weekly_coordinates
    from fetch_news import refresh_weekly_news
    from fetch_poi import refresh_weekly_poi
    from generate_metadata import (generate_robots_txt, generate_security_txt,
                                   generate_sitemap)
    from utils import logger


def refresh_all_data() -> None:
    try:
        logger.info("Starting full data refresh task...")
        generate_security_txt()
        generate_robots_txt()
        refresh_weekly_news()
        refresh_weekly_poi()
        refresh_weekly_coordinates()
        generate_sitemap()
        logger.info("Full data refresh task completed successfully.")
        logger.info(
            f"Next scheduled refresh in {config.UPDATE_INTERVAL_HOURS} hours.")
    except Exception as e:
        logger.error(f"Error during full data refresh: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    refresh_all_data()
