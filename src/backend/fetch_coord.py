import copy
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests

try:
    from . import config
    from .utils import (CoordinateEntry, NewsCoordinate, NewsItem, NewsPOI,
                        NewsStatus, cache_manager, json_manager, logger)
except ImportError:
    import config
    from utils import (CoordinateEntry, NewsCoordinate, NewsItem, NewsPOI,
                       NewsStatus, cache_manager, json_manager, logger)


class CoordinateCoder:

    BASE_URL = "https://nominatim.openstreetmap.org/search?"
    HEADERS = {"User-Agent": f"WorldNewsMapBot/1.0 ({config.CONTACT_INFO})"}
    REQUEST_PARAMS = {"dedupe": 1, "format": "jsonv2"}
    IGNORED_POSITIONS = {"outer space", "cyberspace"}
    PARAM_FALLBACK = (
        ("country", "state", "city", "amenity"),
        ("country", "state", "city"),
        ("city",),
        ("country", "state"),
        ("state",),
        ("country",),
    )

    def __init__(
        self,
        date: str = datetime.now().strftime("%Y-%m-%d"),
        force_refresh: bool = False,
    ):
        self.force_refresh = force_refresh
        self.date = date

    def get_news_list(self) -> None:
        self.news_list = copy.deepcopy(json_manager.read_news_items(self.date))

    def generate_fallback_poi(self, poi: NewsPOI) -> list[NewsPOI]:
        fallback_poi_list = list()
        for params in self.PARAM_FALLBACK:
            fallback_poi = NewsPOI(
                country=poi.country if "country" in params else None,
                state=poi.state if "state" in params else None,
                city=poi.city if "city" in params else None,
                institution=poi.institution if "amenity" in params else None,
            )
            fallback_poi_list.append(fallback_poi)
        return fallback_poi_list

    def request_for_coordinates(self, news_item: NewsItem) -> None:
        if news_item.status not in (
            NewsStatus.POI_FETCHED,
            NewsStatus.COORDINATE_FETCH_FAILED,
            NewsStatus.COORDINATE_FETCHED,
            NewsStatus.NO_VALID_COORDINATE,
        ):
            return
        if not self.force_refresh and news_item.status not in (
            NewsStatus.POI_FETCHED,
            NewsStatus.COORDINATE_FETCH_FAILED,
        ):
            return

        if news_item.poi.country and news_item.poi.country.lower() in self.IGNORED_POSITIONS:
            logger.debug(
                f"News item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...' has an ignored position '{news_item.poi.country}'. Marking as NO_VALID_COORDINATE."
            )
            news_item.coordinate.latitude = -1
            news_item.coordinate.longitude = -1
            news_item.status = NewsStatus.NO_VALID_COORDINATE
            return

        coordinate = self.query(news_item.poi)
        if not coordinate:
            news_item.status = NewsStatus.COORDINATE_FETCH_FAILED
        else:
            news_item.status = NewsStatus.COORDINATE_FETCHED

        news_item.coordinate = coordinate
        return

    def write_cache(self, poi: NewsPOI, coordinate: NewsCoordinate) -> None:
        entry = CoordinateEntry(copy.deepcopy(
            poi), copy.deepcopy(coordinate), datetime.now())
        cache_manager.insert_entry(entry, self.force_refresh)

    def query_cache(self, poi: NewsPOI) -> NewsCoordinate | None:
        if not self.force_refresh and poi:
            cached_coordinate = cache_manager.select_coordinate(poi)
            if cached_coordinate:
                return cached_coordinate
        return None

    def query(self, poi: NewsPOI) -> NewsCoordinate:
        param_mapping = {
            "country": poi.country,
            "state": poi.state,
            "city": poi.city,
            "amenity": poi.institution,
        }
        structed_params = [
            {k: param_mapping[k] for k in fallback if param_mapping[k]}
            for fallback in self.PARAM_FALLBACK
        ]
        free_form_params = [
            [param_mapping[k] for k in fallback if param_mapping[k]]
            for fallback in self.PARAM_FALLBACK
        ]
        null_coordinate = NewsCoordinate(latitude=-1, longitude=-1)

        fallback_poi_list = self.generate_fallback_poi(poi)

        for structed_param_set, free_form_param_set, fallback_poi in zip(
            structed_params, free_form_params, fallback_poi_list
        ):
            try:
                cached_coordinate = self.query_cache(fallback_poi)
                if cached_coordinate:
                    return cached_coordinate
                if not structed_param_set:
                    continue

                logger.debug(
                    f"Querying coordinates with structured params: {structed_param_set}"
                )
                structed_response = requests.get(
                    self.BASE_URL
                    + urlencode({**self.REQUEST_PARAMS, **structed_param_set}),
                    headers=self.HEADERS,
                    timeout=config.REQUEST_TIMEOUT,
                )
                structed_response.raise_for_status()
                structed_data = structed_response.json()
                if (len(structed_data) == 1 or len({item.get("importance") for item in structed_data}) == 1
                        or (len(structed_data) == 2 and {item.get("osm_type") for item in structed_data} == {"relation", "node"})):
                    current_coordinate = NewsCoordinate(
                        latitude=float(structed_data[0].get("lat", -1)),
                        longitude=float(structed_data[0].get("lon", -1)),
                    )
                    for previous_fallback in fallback_poi_list:
                        self.write_cache(previous_fallback, current_coordinate)
                        if previous_fallback == fallback_poi:
                            break
                    return current_coordinate
                time.sleep(config.REQUEST_INTERVAL)

                logger.debug(
                    f"Querying coordinates with free-form params: {free_form_param_set}"
                )
                free_form_response = requests.get(
                    self.BASE_URL
                    + urlencode(
                        {
                            **self.REQUEST_PARAMS,
                            "q": " ".join(filter(None, free_form_param_set)),
                        }
                    ),
                    headers=self.HEADERS,
                    timeout=config.REQUEST_TIMEOUT,
                )
                free_form_response.raise_for_status()
                free_form_data = free_form_response.json()
                if (len(free_form_data) == 1 or len({item.get("importance") for item in free_form_data}) == 1
                        or (len(free_form_data) == 2 and {item.get("osm_type") for item in free_form_data} == {"relation", "node"})):
                    current_coordinate = NewsCoordinate(
                        latitude=float(free_form_data[0].get("lat", -1)),
                        longitude=float(free_form_data[0].get("lon", -1)),
                    )
                    for previous_fallback in fallback_poi_list:
                        self.write_cache(previous_fallback, current_coordinate)
                        if previous_fallback == fallback_poi:
                            break
                    return current_coordinate
                time.sleep(config.REQUEST_INTERVAL)

            except requests.exceptions.Timeout:
                logger.error(
                    "Request timeout while fetching coordinates."
                )
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Connection error while fetching coordinates: {e}"
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Request error while fetching coordinates: {e}"
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error while fetching coordinates: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error while fetching coordinates: {e}",
                    exc_info=True,
                )

        return null_coordinate

    def fetch_coordinates(self) -> None:
        for i, news_item in enumerate(self.news_list):
            logger.info(
                f"Processing news item {i + 1}/{len(self.news_list)}: '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...'"
            )
            self.request_for_coordinates(news_item)

    def save_json(self) -> None:
        json_manager.write_news_items(self.news_list, self.date)

    def work(self) -> None:
        logger.info(f"Starting coordinate fetch for date: {self.date}")
        self.get_news_list()
        self.fetch_coordinates()
        self.save_json()
        logger.info(f"Finished coordinate fetch for date: {self.date}")


def refresh_weekly_coordinates():
    coder = None
    date = None
    try:
        for date_offset in range(7):
            date = (datetime.now() - timedelta(days=date_offset)
                    ).strftime("%Y-%m-%d")
            coder = CoordinateCoder(date=date, force_refresh=False)
            coder.work()
    except KeyboardInterrupt:
        logger.warning(
            f"Process interrupted by user while processing date {date}, stopping gracefully..."
        )
        if coder is not None:
            coder.save_json()
        raise
    except Exception as e:
        logger.error(f"Error processing date {date}: {e}", exc_info=True)
        if coder is not None:
            coder.save_json()
    finally:
        coder = None


if __name__ == "__main__":
    refresh_weekly_coordinates()
