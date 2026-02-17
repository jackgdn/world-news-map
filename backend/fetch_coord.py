import copy
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from fake_useragent import UserAgent

import config
from utils import (CoordinateEntry, NewsCoordinate, NewsItem, NewsPOI,
                   NewsStatus, cache_manager, json_manager, logger)


class CoordinateCoder:

    BASE_URL = "https://nominatim.openstreetmap.org/search?"
    HEADERS = {"User-Agent": UserAgent().random}
    REQUEST_PARAMS = {"dedupe": 1, "format": "jsonv2"}
    IGNORED_POSITIONS = {"outer space", "cyberspace"}
    SPECIAL_POSITIONS = {"antarctica"}

    def __init__(
        self,
        date: str = datetime.now().strftime("%Y-%m-%d"),
        force_refresh: bool = False,
    ):
        self.force_refresh = force_refresh
        self.date = date

    def get_news_list(self) -> None:
        self.news_list = copy.deepcopy(json_manager.read_news_items(self.date))

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

        if news_item.poi.country and news_item.poi.country.lower() in self.SPECIAL_POSITIONS:
            logger.debug(
                f"News item '{news_item.description[:config.LOG_DESCRIPTION_MAX_LENGTH]}...' has a special position '{news_item.poi.country}'. Using special query."
            )
            special_coordinate = self.special_query(news_item.poi)
            if special_coordinate:
                news_item.coordinate = special_coordinate
                news_item.status = NewsStatus.COORDINATE_FETCHED
                self.write_cache(news_item.poi, special_coordinate)
                return

        coordinate, fallback_level = self.query(news_item.poi)
        if not coordinate:
            news_item.status = NewsStatus.COORDINATE_FETCH_FAILED
        else:
            news_item.status = NewsStatus.COORDINATE_FETCHED
            poi = copy.deepcopy(news_item.poi)

            current_level = 0
            for field in ["institution", "city", "state", "country"]:
                if fallback_level == -1 or current_level > fallback_level:
                    break
                if poi:
                    self.write_cache(poi, coordinate)
                setattr(poi, field, None)

        news_item.coordinate = coordinate
        return

    def special_query(self, poi: NewsPOI) -> NewsCoordinate | None:
        if poi.country and poi.country.lower() == "antarctica" and poi.institution is None:
            response = requests.get(
                self.BASE_URL
                + urlencode({
                    **self.REQUEST_PARAMS,
                    "q": "antarctica",
                }),
                headers=self.HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()[0]
            return NewsCoordinate(latitude=float(data.get("lat", -1)), longitude=float(data.get("lon", -1)))

    def write_cache(self, poi: NewsPOI, coordinate: NewsCoordinate) -> None:
        entry = CoordinateEntry(copy.deepcopy(
            poi), copy.deepcopy(coordinate), datetime.now())
        cache_manager.insert_entry(entry)

    def query_cache(self, poi: NewsPOI) -> NewsCoordinate | None:
        if not self.force_refresh:
            cached_coordinate = cache_manager.select_coordinate(poi)
            if cached_coordinate:
                return cached_coordinate
        return None

    def build_fallback_poi_list(self, poi: NewsPOI) -> list[NewsPOI]:
        fallback_poi_list = list()

        p0 = NewsPOI()
        p0.country = poi.country
        p0.state = poi.state
        p0.city = poi.city
        p0.institution = poi.institution
        fallback_poi_list.append(p0)

        p1 = NewsPOI()
        p1.country = poi.country
        p1.state = poi.state
        p1.city = poi.city
        fallback_poi_list.append(p1)

        p3 = NewsPOI()
        p3.country = poi.country
        p3.state = poi.state
        fallback_poi_list.append(p3)

        p4 = NewsPOI()
        p4.country = poi.country
        fallback_poi_list.append(p4)

        return fallback_poi_list

    def query(self, poi: NewsPOI) -> tuple[NewsCoordinate, int]:
        param_mapping = {
            "country": poi.country,
            "state": poi.state,
            "city": poi.city,
            "amenity": poi.institution,
        }
        param_fallback = (
            ("country", "state", "city", "amenity"),
            ("country", "state", "city"),
            ("country", "state"),
            ("country",),
        )
        structed_params = [
            {k: param_mapping[k] for k in fallback if param_mapping[k]}
            for fallback in param_fallback
        ]
        free_form_params = [
            [param_mapping[k] for k in fallback if param_mapping[k]]
            for fallback in param_fallback
        ]
        null_coordinate = NewsCoordinate(latitude=-1, longitude=-1)

        fallback_poi_list = self.build_fallback_poi_list(poi)

        fallback_level = 0
        for structed_param_set, free_form_param_set, fallback_poi in zip(
            structed_params, free_form_params, fallback_poi_list
        ):
            try:
                cached_coordinate = self.query_cache(fallback_poi)
                if cached_coordinate:
                    return cached_coordinate, -1
                if not structed_param_set:
                    return null_coordinate, fallback_level

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
                if len(structed_data) == 1:
                    return NewsCoordinate(
                        latitude=float(structed_data[0].get("lat", -1)),
                        longitude=float(structed_data[0].get("lon", -1)),
                    ), fallback_level
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
                if len(free_form_data) == 1:
                    return NewsCoordinate(
                        latitude=float(free_form_data[0].get("lat", -1)),
                        longitude=float(free_form_data[0].get("lon", -1)),
                    ), fallback_level
                time.sleep(config.REQUEST_INTERVAL)

                fallback_level += 1

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

        return null_coordinate, fallback_level

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
