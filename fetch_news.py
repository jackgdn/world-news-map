import time
from datetime import datetime, timedelta

import requests
from fake_useragent import UserAgent
from lxml import html

from config import REQUEST_INTERVAL, REEQUEST_TIMEOUT
from utils import NewsItem, NewsLink, NewsStatus, json_manager, logger


class WikiNewsScraper:

    BASE_URL = "https://en.wikipedia.org/wiki/Portal:Current_events"
    HEADERS = {"User-Agent": UserAgent().random}

    def __init__(
        self,
        date: str = datetime.now().strftime("%Y-%m-%d"),
        force_refresh: bool = False,
    ):
        self.force_refresh = force_refresh
        self.date = date

    def fetch_news(self) -> None:
        try:
            response = requests.get(
                self.BASE_URL, headers=self.HEADERS, timeout=REEQUEST_TIMEOUT
            )
            if response.status_code == 200:
                logger.info(f"Successfully fetched news for {self.date}.")
                self.parse_news(response.content)
            else:
                logger.error(f"Failed to fetch news: {response.status_code}")
                self.news_list = list()

        except requests.exceptions.Timeout:
            logger.error("Request timeout while fetching news.")
            self.news_list = list()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching news: {e}")
            self.news_list = list()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching news: {e}")
            self.news_list = list()
        except Exception as e:
            logger.error(f"Unexpected error while fetching news: {e}", exc_info=True)
            self.news_list = list()

    def parse_news(self, html_content: bytes) -> None:
        tree = html.fromstring(html_content)
        event_blocks = tree.xpath(
            '//div[@class="p-current-events-events"]//div[@class="current-events-main vevent"]'
        )

        for event_block in event_blocks:
            try:
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

                    current_news_item = NewsItem(
                        status=NewsStatus.FETCHED,
                        date=date_text,
                        description=description,
                        links=links,
                    )
                    if current_news_item not in self.news_list:
                        self.news_list.append(current_news_item)
            except IndexError:
                logger.warning(
                    "Missing expected date element in event block, skipping."
                )
                continue
            except Exception as e:
                logger.warning(f"Error parsing event block: {e}")
                continue

        logger.info(f"Parsed {len(self.news_list)} news items for date: {self.date}.")

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

    def get_news_list(self) -> None:
        if not self.force_refresh:
            logger.info(f"Attempting to read existing news items for {self.date}.")
            self.news_list = json_manager.read_news_items(self.date)
            if self.news_list:
                logger.info(
                    f"Found {len(self.news_list)} existing news items for {self.date}, skipping fetch."
                )
        else:
            logger.info(
                f"Force refresh enabled, ignoring existing news items for {self.date}."
            )
            self.news_list = list()

    def save_json(self) -> None:
        json_manager.write_news_items(self.news_list, self.date)

    def work(self) -> None:
        logger.info(f"Starting news fetch for date: {self.date}")
        self.get_news_list()
        self.fetch_news()
        self.save_json()
        logger.info(f"Completed news fetch and save for date: {self.date}")


def fetch_current_news():
    scraper = WikiNewsScraper()
    try:
        scraper.work()
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user, stopping gracefully...")
        scraper.save_json()
    except Exception as e:
        logger.error(f"Error during POI fetch: {e}", exc_info=True)
        scraper.save_json()


def refresh_weekly_news():
    for date_offset in range(7):
        date = (datetime.now() - timedelta(days=date_offset)).strftime("%Y-%m-%d")
        scraper = WikiNewsScraper(date=date, force_refresh=False)
        try:
            scraper.work()
            logger.info(
                f"Waiting {REQUEST_INTERVAL} seconds before processing next date..."
            )
            time.sleep(REQUEST_INTERVAL)
        except KeyboardInterrupt:
            logger.warning(
                f"Process interrupted by user while processing date {date}, stopping gracefully..."
            )
            scraper.save_json()
            raise
        except Exception as e:
            logger.error(f"Error processing date {date}: {e}", exc_info=True)
            scraper.save_json()


if __name__ == "__main__":
    refresh_weekly_news()
