import os
from datetime import datetime, timedelta

import requests
from fake_useragent import UserAgent
from lxml import html

from utils import JSONManager, NewsItem, NewsLink, logger


class WikiNewsScraper:

    BASE_URL = "https://en.wikipedia.org/wiki/Portal:Current_events"
    HEADERS = {"User-Agent": UserAgent().random}

    def __init__(
        self,
        date: str = datetime.now().strftime("%Y-%m-%d"),
        news_dir: str = "news",
        force_refresh: bool = False,
    ):
        self.logger = logger
        if not force_refresh and os.path.exists(os.path.join(news_dir, f"{date}.json")):
            logger.info(f"News for {date} already exists. Skipping fetch.")
            return
        elif force_refresh and os.path.exists(os.path.join(news_dir, f"{date}.json")):
            os.remove(os.path.join(news_dir, f"{date}.json"))
            logger.info(f"Existing news for {date} removed due to force refresh.")
        self.date = date
        self.json_manager = JSONManager(news_dir)

    def fetch_news(self) -> None:
        response = requests.get(self.BASE_URL, headers=self.HEADERS)
        if response.status_code == 200:
            logger.info(f"Successfully fetched news for {self.date}.")
            self.news_items = self.parse_news(response.content)
        else:
            logger.error(f"Failed to fetch news: {response.status_code}")
            self.news_items = list()

    def parse_news(self, html_content: bytes) -> list[NewsItem]:
        tree = html.fromstring(html_content)
        event_blocks = tree.xpath(
            '//div[@class="p-current-events-events"]//div[@class="current-events-main vevent"]'
        )
        news_items = list()
        for event_block in event_blocks:
            date_text = event_block.xpath(
                './/span[@class="bday dtstart published updated itvstart"]/text()'
            )[0]
            if date_text != self.date:
                continue
            item_elements = event_block.xpath(
                './/div[@class="current-events-content description"]//li[not(.//li)]'
            )
            for item_element in item_elements:
                description, links = self.extract_data(item_element)
                if not description:
                    continue
                news_items.append(NewsItem(date_text, description, links))
        return news_items

    def extract_data(
        self, item_element: html.HtmlElement
    ) -> tuple[str, list[NewsLink]]:
        link_nodes = item_element.xpath('.//a[@rel="nofollow"]')
        links = list()
        total_link_chars = 0
        link_count = 0
        for link_node in link_nodes:
            link_text = link_node.text_content()
            total_link_chars += len(link_text)
            total_link_chars += link_count
            link_count += 1
            link_text = link_text.strip()
            url = link_node.get("href")
            links.append(NewsLink(link_text, url))

        full_text = "".join(item_element.itertext())
        description = full_text[:-total_link_chars].strip()
        return description, links

    def save_json(self) -> None:
        self.json_manager.write_news_items(self.news_items, self.date)

    def work(self) -> None:
        self.fetch_news()
        self.save_json()


def fetch_current_news():
    scraper = WikiNewsScraper()
    scraper.work()


def refresh_news():
    for date_offset in range(0, 7):
        date = (datetime.now() - timedelta(days=date_offset)).strftime("%Y-%m-%d")
        scraper = WikiNewsScraper(date=date, force_refresh=True)
        scraper.work()


if __name__ == "__main__":
    refresh_news()
