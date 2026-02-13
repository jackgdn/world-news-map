import json
import logging
import os
from datetime import datetime


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


class NewsItem:

    def __init__(self, date: str, description: str, links: list[NewsLink]):
        self.date = date
        self.description = description
        self.links = links


class JSONManager:

    def __init__(self, news_dir: str = "news"):
        self.news_dir = news_dir
        os.makedirs(news_dir, exist_ok=True)
        logger.info(f"JSONManager initialized with news directory: {news_dir}")

    def write_news_items(self, news_items: list[NewsItem], date: str):
        json_path = os.path.join(self.news_dir, f"{date}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "status": "fetched",
                        "date": news.date,
                        "description": news.description,
                        "links": [
                            {"source": link.source, "url": link.url}
                            for link in news.links
                        ],
                        "poi": {
                            "country": None,
                            "state": None,
                            "city": None,
                            "institution": None,
                        },
                        "position": {
                            "latitude": None,
                            "longitude": None,
                        },
                    }
                    for news in news_items
                ],
                f,
                ensure_ascii=False,
                indent=4,
            )
            logger.info(f"News items for {date} written to {json_path}")
