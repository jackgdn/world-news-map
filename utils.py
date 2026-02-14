import json
import logging
import os
from datetime import datetime
from enum import Enum

from config import NEWS_PATH


class Logger:

    def __init__(
        self,
        log_name="wnm",
        log_file="logs/{date}.log".format(date=datetime.now().strftime("%Y-%m-%d")),
        log_level=logging.DEBUG,
    ):
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(log_level)
        self.logger.handlers.clear()
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg, exc_info=False):
        self.logger.error(msg, exc_info=exc_info)

    def critical(self, msg):
        self.logger.critical(msg)


logger = Logger()


class NewsLink:

    def __init__(self, source: str, url: str):
        self.source = source
        self.url = url


class NewsPOI:

    def __init__(
        self,
        country: str | None = None,
        state: str | None = None,
        city: str | None = None,
        institution: str | None = None,
    ):
        self.country = country
        self.state = state
        self.city = city
        self.institution = institution


class NewsPosition:

    def __init__(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
    ):
        self.latitude = latitude
        self.longitude = longitude


class NewsStatus(Enum):
    FETCHED = "fetched"
    POI_FETCHED = "poi_fetched"
    POSITION_FETCHED = "position_fetched"
    POI_FETCH_FAILED = "poi_fetch_failed"
    POSITION_FETCH_FAILED = "position_fetch_failed"


class NewsItem:

    def __init__(
        self,
        status: NewsStatus,
        date: str,
        description: str,
        links: list[NewsLink],
        poi: NewsPOI | None = None,
        position: NewsPosition | None = None,
    ):
        self.status = status
        self.date = date
        self.description = description
        self.links = links
        self.poi = poi if poi is not None else NewsPOI()
        self.position = position if position is not None else NewsPosition()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NewsItem):
            return False
        return self.description == other.description and self.date == other.date


class JSONManager:

    def __init__(self):
        self.news_dir = NEWS_PATH
        try:
            os.makedirs(self.news_dir, exist_ok=True)
            logger.info(f"JSONManager initialized with news directory: {self.news_dir}")
        except Exception as e:
            logger.error(
                f"Error creating news directory {self.news_dir}: {e}", exc_info=True
            )
            raise

    def write_news_items(self, news_items: list[NewsItem], date: str) -> None:

        if not news_items:
            logger.error(f"No news items to write for date: {date}.")
            return

        json_path = os.path.join(self.news_dir, f"{date}.json")

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "status": news.status.value,
                            "date": news.date,
                            "description": news.description,
                            "links": [
                                {"source": link.source, "url": link.url}
                                for link in news.links
                            ],
                            "poi": {
                                "country": news.poi.country,
                                "state": news.poi.state,
                                "city": news.poi.city,
                                "institution": news.poi.institution,
                            },
                            "position": {
                                "latitude": news.position.latitude,
                                "longitude": news.position.longitude,
                            },
                        }
                        for news in news_items
                    ],
                    f,
                    ensure_ascii=False,
                    indent=4,
                )
                logger.info(f"News items for {date} written to {json_path}")
        except Exception as e:
            logger.error(f"Error writing news items to {json_path}: {e}", exc_info=True)

    def read_news_items(self, date: str) -> list[NewsItem]:
        json_path = os.path.join(self.news_dir, f"{date}.json")
        if not os.path.exists(json_path):
            logger.warning(f"No news file found for {date} at {json_path}")
            return list()
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                news_items = list()
                for item in data:
                    links = [
                        NewsLink(link["source"], link["url"])
                        for link in item.get("links", [])
                    ]
                    poi_data = item.get("poi", {})
                    poi = NewsPOI(
                        country=poi_data.get("country"),
                        state=poi_data.get("state"),
                        city=poi_data.get("city"),
                        institution=poi_data.get("institution"),
                    )
                    position_data = item.get("position", {})
                    position = NewsPosition(
                        latitude=position_data.get("latitude"),
                        longitude=position_data.get("longitude"),
                    )
                    news_item = NewsItem(
                        status=NewsStatus(item.get("status")),
                        date=item.get("date"),
                        description=item.get("description"),
                        links=links,
                        poi=poi,
                        position=position,
                    )
                    news_items.append(news_item)
                logger.info(f"Read {len(news_items)} news items from {json_path}")
                return news_items
        except ValueError as e:
            logger.error(f"JSON decode error for {json_path}: {e}", exc_info=True)
            return list()
        except Exception as e:
            logger.error(
                f"Error reading news items from {json_path}: {e}", exc_info=True
            )
            return list()


json_manager = JSONManager()
