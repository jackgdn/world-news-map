import copy
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from openai import OpenAI

try:
    from . import config
    from .utils import NewsItem, NewsPOI, NewsStatus, json_manager, logger
except ImportError:
    import config
    from utils import NewsItem, NewsPOI, NewsStatus, json_manager, logger


class AIChatter:

    PROMPT_FILE = Path(__file__).parent.parent.parent / "prompt.txt"

    def __init__(
        self,
        date: str = datetime.now().strftime("%Y-%m-%d"),
        force_refresh: bool = False,
    ):

        self.client = OpenAI(
            base_url=config.LANGUAGE_MODEL_BASE_URL,
            api_key=config.LANGUAGE_MODEL_API_KEY,
        )

        try:
            with open(self.PROMPT_FILE, "r") as f:
                self.prompt = f.read()
        except Exception as e:
            logger.error(
                f"Error reading prompt from {self.PROMPT_FILE}: {e}", exc_info=True
            )
            raise e

        self.force_refresh = force_refresh
        self.date = date

    def get_news_list(self) -> None:
        self.news_list = copy.deepcopy(json_manager.read_news_items(self.date))

    def request_for_poi(self, news_item: NewsItem) -> None:
        if not self.force_refresh and news_item.status not in (
            NewsStatus.FETCHED,
            NewsStatus.POI_FETCH_FAILED,
        ):
            return

        for attempt in range(config.MAX_RETRIES):

            if attempt == 0:
                logger.info(
                    f"Fetching POI for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...' (Attempt 1/{config.MAX_RETRIES})"
                )

            try:
                response = self.client.chat.completions.create(
                    model=config.LANGUAGE_MODEL_NAME,
                    messages=[
                        {
                            "role": "user",
                            "content": self.prompt.format(desc=news_item.description),
                        }
                    ],
                    stream=False,
                    extra_body=config.LANGUAGE_MODEL_EXTRA_PARAMS,
                )
                logger.debug(
                    f"Waiting for {config.REQUEST_INTERVAL} seconds after API calls."
                )
                time.sleep(config.REQUEST_INTERVAL)
                answer_text = response.choices[0].message.content
            except Exception as e:
                logger.error(
                    f"Error during OpenAI API call: {e}", exc_info=True)
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < config.MAX_RETRIES - 1:
                    logger.info(
                        f"Retrying... (Attempt {attempt + 2}/{config.MAX_RETRIES})"
                    )
                continue

            if answer_text is None or answer_text.strip() == "":
                logger.warning(
                    f"Empty response for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...'"
                )
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < config.MAX_RETRIES - 1:
                    logger.info(
                        f"Retrying... (Attempt {attempt + 2}/{config.MAX_RETRIES})"
                    )
                continue

            try:
                json_text = self.extract_json_text(answer_text)
                poi_json = json.loads(json_text).get("poi")

                if poi_json is None:
                    logger.warning(
                        f"No 'poi' field in response for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...'"
                    )
                    news_item.status = NewsStatus.POI_FETCH_FAILED
                    if attempt < config.MAX_RETRIES - 1:
                        logger.info(
                            f"Retrying... (Attempt {attempt + 2}/{config.MAX_RETRIES})"
                        )
                    continue

                poi = NewsPOI(
                    country=poi_json.get("country"),
                    state=poi_json.get("state"),
                    city=poi_json.get("city"),
                    institution=poi_json.get("institution"),
                )
                if not poi:
                    logger.warning(
                        f"All POI fields are empty for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...'"
                    )
                    logger.debug(f"Received response: {answer_text}")
                    news_item.status = NewsStatus.POI_FETCH_FAILED
                    if attempt < config.MAX_RETRIES - 1:
                        logger.info(
                            f"Retrying... (Attempt {attempt + 2}/{config.MAX_RETRIES})"
                        )
                    continue

                news_item.poi = poi
                news_item.status = NewsStatus.POI_FETCHED
                logger.info(
                    f"Successfully fetched POI for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...'"
                )
                return

            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...': {e}",
                    exc_info=True,
                )
                logger.error(f"Received response: {answer_text}")
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < config.MAX_RETRIES - 1:
                    logger.info(
                        f"Retrying... (Attempt {attempt + 2}/{config.MAX_RETRIES})"
                    )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing response for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...': {e}",
                    exc_info=True,
                )
                logger.debug(f"Received response: {answer_text}")
                news_item.status = NewsStatus.POI_FETCH_FAILED
                if attempt < config.MAX_RETRIES - 1:
                    logger.info(
                        f"Retrying... (Attempt {attempt + 2}/{config.MAX_RETRIES})"
                    )

        logger.warning(
            f"Failed to fetch POI for news item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...' after {config.MAX_RETRIES} attempts."
        )
        return

    def extract_json_text(self, text: str) -> str:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        else:
            return text.strip()

    def save_json(self) -> None:
        json_manager.write_news_items(self.news_list, self.date)

    def fetch_pois(self) -> None:
        for i, news_item in enumerate(self.news_list):
            self.request_for_poi(news_item)

    def work(self) -> None:
        logger.info(f"Starting POI fetch for date: {self.date}")
        self.get_news_list()
        self.fetch_pois()
        self.save_json()
        logger.info(f"Completed POI fetch for date: {self.date}")


def refresh_weekly_poi():
    chatter = None
    date = None
    try:
        for date_offset in range(7):
            date = (datetime.now() - timedelta(days=date_offset)
                    ).strftime("%Y-%m-%d")
            chatter = AIChatter(date=date, force_refresh=False)
            chatter.work()
    except KeyboardInterrupt:
        logger.warning(
            f"Process interrupted by user while processing date {date}, stopping gracefully..."
        )
        if chatter is not None:
            chatter.save_json()
        raise
    except Exception as e:
        logger.error(f"Error processing date {date}: {e}", exc_info=True)
        if chatter is not None:
            chatter.save_json()
    finally:
        chatter = None


if __name__ == "__main__":
    refresh_weekly_poi()
