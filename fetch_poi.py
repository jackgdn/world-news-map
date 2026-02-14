import json
import re
import time
from datetime import datetime, timedelta

from openai import OpenAI

from config import (
    LANGUAGE_MODEL_API_KEY,
    LANGUAGE_MODEL_API_URL,
    LANGUAGE_MODEL_NAME,
    MAX_RETRIES,
    PROMPT_PATH,
    REQUEST_INTERVAL,
)
from utils import NewsItem, NewsPOI, NewsStatus, json_manager, logger


class AIChatter:

    def __init__(
        self,
        date: str = datetime.now().strftime("%Y-%m-%d"),
        force_refresh: bool = False,
    ):

        self.client = OpenAI(
            base_url=LANGUAGE_MODEL_API_URL,
            api_key=LANGUAGE_MODEL_API_KEY,
        )

        try:
            with open(PROMPT_PATH, "r") as f:
                self.prompt = f.read()
        except Exception as e:
            logger.error(f"Error reading prompt from {PROMPT_PATH}: {e}", exc_info=True)
            raise e

        self.model = LANGUAGE_MODEL_NAME
        self.force_refresh = force_refresh
        self.date = date

    def get_news_list(self) -> None:
        self.news_list = json_manager.read_news_items(self.date)

    def request_for_poi(self, news_item: NewsItem) -> NewsItem:
        for attempt in range(MAX_RETRIES):
            if not self.force_refresh and news_item.status not in (
                "fetched",
                "poi_fetch_failed",
            ):
                return news_item

            if attempt == 0:
                logger.info(
                    f"Fetching POI for news item '{news_item.description[:15]}...' (Attempt 1/{MAX_RETRIES})"
                )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": self.prompt.format(desc=news_item.description),
                        }
                    ],
                    stream=False,
                )
                logger.debug(f"Waiting for {REQUEST_INTERVAL} seconds after API calls.")
                time.sleep(REQUEST_INTERVAL)
                answer_text = response.choices[0].message.content
            except Exception as e:
                logger.error(f"Error during OpenAI API call: {e}", exc_info=True)
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying... (Attempt {attempt + 2}/{MAX_RETRIES})")
                continue

            if answer_text is None or answer_text.strip() == "":
                logger.warning(
                    f"Empty response for news item '{news_item.description[:15]}...'"
                )
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying... (Attempt {attempt + 2}/{MAX_RETRIES})")
                continue

            try:
                json_text = self.extract_json_text(answer_text)
                poi_json = json.loads(json_text).get("poi")

                if poi_json is None:
                    logger.warning(
                        f"No 'poi' field in response for news item '{news_item.description[:15]}...'"
                    )
                    news_item.status = NewsStatus.POI_FETCH_FAILED
                    if attempt < MAX_RETRIES - 1:
                        logger.info(
                            f"Retrying... (Attempt {attempt + 2}/{MAX_RETRIES})"
                        )
                    continue

                poi = NewsPOI(
                    country=poi_json.get("country"),
                    state=poi_json.get("state"),
                    city=poi_json.get("city"),
                    institution=poi_json.get("institution"),
                )
                news_item.poi = poi
                news_item.status = NewsStatus.POI_FETCHED
                logger.info(
                    f"Successfully fetched POI for news item '{news_item.description[:15]}...'"
                )
                return news_item

            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error for news item '{news_item.description[:15]}...': {e}",
                    exc_info=True,
                )
                logger.error(f"Received response: {answer_text}")
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying... (Attempt {attempt + 2}/{MAX_RETRIES})")
            except Exception as e:
                logger.error(
                    f"Unexpected error processing response for news item '{news_item.description[:15]}...': {e}",
                    exc_info=True,
                )
                logger.debug(f"Received response: {answer_text}")
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying... (Attempt {attempt + 2}/{MAX_RETRIES})")

        logger.warning(
            f"Failed to fetch POI for news item '{news_item.description[:15]}...' after {MAX_RETRIES} attempts."
        )
        return news_item

    def extract_json_text(self, text: str) -> str:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        else:
            return text.strip()

    def save_json(
        self,
    ) -> None:
        json_manager.write_news_items(self.news_list, self.date)

    def fetch_pois(self) -> None:
        for i, news_item in enumerate(self.news_list):
            news_item_poi = self.request_for_poi(news_item)
            self.news_list[i] = news_item_poi

    def work(self) -> None:
        logger.info(f"Starting POI fetch for date: {self.date}")
        self.get_news_list()
        self.fetch_pois()
        self.save_json()
        logger.info(f"Completed POI fetch for date: {self.date}")


def fetch_current_poi():
    chatter = AIChatter()
    try:
        chatter.work()
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user, stopping gracefully...")
        chatter.save_json()
    except Exception as e:
        logger.error(f"Error during POI fetch: {e}", exc_info=True)
        chatter.save_json()


def refresh_weekly_poi():
    for date_offset in range(7):
        date = (datetime.now() - timedelta(days=date_offset)).strftime("%Y-%m-%d")
        chatter = AIChatter(date=date, force_refresh=False)
        try:
            chatter.work()
        except KeyboardInterrupt:
            logger.warning(
                f"Process interrupted by user while processing date {date}, stopping gracefully..."
            )
            chatter.save_json()
            raise
        except Exception as e:
            logger.error(f"Error processing date {date}: {e}", exc_info=True)
            chatter.save_json()


if __name__ == "__main__":
    refresh_weekly_poi()
