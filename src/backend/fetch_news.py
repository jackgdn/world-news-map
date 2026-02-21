import copy
import time
from datetime import datetime, timedelta

import requests
from lxml import html

try:
    from . import config
    from .utils import NewsItem, NewsLink, NewsStatus, json_manager, logger
except ImportError:
    import config
    from utils import NewsItem, NewsLink, NewsStatus, json_manager, logger


class WikiNewsScraper:

    BASE_URL = "https://en.wikipedia.org/w/api.php?action=parse&format=json&page=Portal:Current%20events&prop=text&formatversion=2"
    HEADERS = {"User-Agent": f"WorldNewsMapBot/1.0 ({config.CONTACT_INFO})"}

    def __init__(
        self,
        force_refresh: bool = False,
    ):
        self.force_refresh = force_refresh

    def fetch_news(self) -> bool:
        try:
            response = requests.get(
                self.BASE_URL, headers=self.HEADERS, timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            logger.info("Successfully fetched news.")
            self.tree = html.fromstring(response.json().get(
                "parse", {}).get("text", "").encode("utf-8"))
            return True

        except requests.exceptions.Timeout:
            logger.error("Request timeout while fetching news.")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching news: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching news: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error while fetching news: {e}", exc_info=True)
        finally:
            return False

    def parse_news(self, date: str) -> None:
        event_blocks = self.tree.xpath(
            '//div[@class="p-current-events-events"]//div[@class="current-events-main vevent"]'
        )

        for event_block in event_blocks:
            try:
                date_text = event_block.xpath(
                    './/span[@class="bday dtstart published updated itvstart"]/text()'
                )[0]
                if date_text != date:
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

                    repetitive = False
                    for i, existing_item in enumerate(self.news_list):
                        if existing_item == current_news_item:
                            repetitive = True
                            break
                        if existing_item.is_similar(current_news_item):
                            self.news_list[i].description = current_news_item.description
                            self.news_list[i].links = current_news_item.links
                            repetitive = True
                            break
                    if not repetitive:
                        self.news_list.append(current_news_item)

            except IndexError:
                logger.warning(
                    "Missing expected date element in event block, skipping."
                )
                continue
            except Exception as e:
                logger.warning(f"Error parsing event block: {e}")
                continue

        logger.info(
            f"Parsed {len(self.news_list)} news items for date: {date}.")

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
        return description, copy.deepcopy(links)

    def get_news_list(self, date: str) -> None:
        if not self.force_refresh:
            logger.info(
                f"Attempting to read existing news items for {date}.")
            self.news_list = copy.deepcopy(
                json_manager.read_news_items(date))
            if self.news_list:
                logger.info(
                    f"Found {len(self.news_list)} existing news items for {date}."
                )
        else:
            logger.info(
                f"Force refresh enabled, ignoring existing news items for {date}."
            )
            self.news_list = list()

    def save_json(self, date: str) -> None:
        json_manager.write_news_items(self.news_list, date)

    def work(self, date: str) -> None:
        logger.info(f"Starting news fetch for date: {date}")
        self.get_news_list(date)
        self.parse_news(date)
        self.save_json(date)
        logger.info(f"Completed news fetch and save for date: {date}")


def refresh_weekly_news():
    scraper = WikiNewsScraper(force_refresh=False)
    scraper.fetch_news()
    if not scraper.fetch_news():
        logger.error("Fetch failed; aborting to avoid parsing without tree.")
        return

    date = None
    try:
        for date_offset in range(7):
            date = (datetime.now() - timedelta(days=date_offset)
                    ).strftime("%Y-%m-%d")
            scraper.work(date)
            logger.info(
                f"Waiting {config.REQUEST_INTERVAL} seconds before processing next date..."
            )
            time.sleep(config.REQUEST_INTERVAL)
    except KeyboardInterrupt:
        logger.warning(
            f"Process interrupted by user while processing date {date}, stopping gracefully..."
        )
        if date is not None:
            scraper.save_json(date)
        raise
    except Exception as e:
        logger.error(f"Error processing date {date}: {e}", exc_info=True)
        if date is not None:
            scraper.save_json(date)


if __name__ == "__main__":
    refresh_weekly_news()
