import copy
import json
import os
import sys
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import msgpack

try:
    from . import config
except ImportError:
    import config

try:
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    src_dir = os.path.dirname(backend_dir)
    if src_dir not in sys.path:
        sys.path.append(src_dir)
    from common.logger import backend_logger as logger
except Exception as e:
    print(f"Error importing modules: {e}")
    raise


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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NewsPOI):
            return False
        return (
            self.country == other.country
            and self.state == other.state
            and self.city == other.city
            and self.institution == other.institution
        )

    def __str__(self) -> str:
        parts = [self.country, self.state, self.city, self.institution]
        return ", ".join(part for part in parts if part)

    def __bool__(self) -> bool:
        INVALID_VALUES = {"none", "n/a", "null", "unknown", ""}
        for field in [self.country, self.state, self.city, self.institution]:
            if field and field.strip().lower() not in INVALID_VALUES:
                return True
        return False


class NewsCoordinate:

    def __init__(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
    ):
        self.latitude = latitude
        self.longitude = longitude

    def __bool__(self) -> bool:
        return self.latitude is not None and self.longitude is not None and self.latitude != -1 and self.longitude != -1


class NewsStatus(Enum):
    FETCHED = "fetched"
    POI_FETCHED = "poi_fetched"
    POI_FETCH_FAILED = "poi_fetch_failed"
    COORDINATE_FETCHED = "coordinate_fetched"
    COORDINATE_FETCH_FAILED = "coordinate_fetch_failed"
    NO_VALID_COORDINATE = "no_valid_coordinate"
    UNKNOWN = "unknown"


class NewsItem:

    def __init__(
        self,
        status: NewsStatus,
        date: str,
        description: str,
        links: list[NewsLink],
        poi: NewsPOI | None = None,
        coordinate: NewsCoordinate | None = None,
    ):
        self.status = status
        self.date = date
        self.description = description
        self.links = links
        self.poi = copy.deepcopy(poi) if poi is not None else NewsPOI()
        self.coordinate = copy.deepcopy(
            coordinate) if coordinate is not None else NewsCoordinate()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NewsItem):
            return False
        return self.description == other.description and self.date == other.date

    def is_similar(self, other: object) -> bool:
        if not isinstance(other, NewsItem):
            return False
        if self == other:
            return False
        if self.date != other.date:
            return False
        for self_link in self.links:
            for other_link in other.links:
                if self_link.url == other_link.url:
                    return True
        return False


class JSONManager:

    NEWS_FILE_DIR = Path(__file__).parent.parent / \
        "frontend" / "public" / "news"

    def __init__(self):
        try:
            os.makedirs(self.NEWS_FILE_DIR, exist_ok=True)
            logger.debug(
                f"JSONManager initialized with news directory: {self.NEWS_FILE_DIR}")
        except Exception as e:
            logger.error(
                f"Error creating news directory {self.NEWS_FILE_DIR}: {e}", exc_info=True
            )
            raise

    def write_news_items(self, news_items: list[NewsItem], date: str) -> None:

        if not news_items:
            logger.error(f"No news items to write for date: {date}.")
            return

        json_path = os.path.join(self.NEWS_FILE_DIR, f"{date}.json")

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
                            "coordinate": {
                                "latitude": news.coordinate.latitude,
                                "longitude": news.coordinate.longitude,
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
            logger.error(
                f"Error writing news items to {json_path}: {e}", exc_info=True)

    def read_news_items(self, date: str) -> list[NewsItem]:
        json_path = os.path.join(self.NEWS_FILE_DIR, f"{date}.json")
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
                        for link in item.get("links", list())
                    ]
                    poi_data = item.get("poi", {})
                    poi = NewsPOI(
                        country=poi_data.get("country"),
                        state=poi_data.get("state"),
                        city=poi_data.get("city"),
                        institution=poi_data.get("institution"),
                    )
                    coordinate_data = item.get("coordinate", {})
                    coordinate = NewsCoordinate(
                        latitude=coordinate_data.get("latitude"),
                        longitude=coordinate_data.get("longitude"),
                    )
                    status_value = item.get("status")
                    if status_value not in NewsStatus._value2member_map_:
                        status_value = NewsStatus.UNKNOWN
                    news_item = NewsItem(
                        status=NewsStatus(status_value),
                        date=item.get("date"),
                        description=item.get("description"),
                        links=links,
                        poi=poi,
                        coordinate=coordinate,
                    )
                    news_items.append(news_item)
                logger.info(
                    f"Read {len(news_items)} news items from {json_path}")
                return news_items
        except ValueError as e:
            logger.error(
                f"JSON decode error for {json_path}: {e}", exc_info=True)
            return list()
        except Exception as e:
            logger.error(
                f"Error reading news items from {json_path}: {e}", exc_info=True
            )
            return list()


json_manager = JSONManager()


class CoordinateEntry:

    def __init__(self, poi: NewsPOI, coordinate: NewsCoordinate, timestamp: datetime):
        self.poi = copy.deepcopy(poi)
        self.coordinate = copy.deepcopy(coordinate)
        self.timestamp = timestamp

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CoordinateEntry):
            return False
        return self.poi == other.poi

    def __str__(self) -> str:
        return str(self.poi)

    def __bool__(self) -> bool:
        return bool(self.coordinate)


class CoordinateCacheManager:

    EXPIRATION_DAYS = max(config.CACHE_EXPIRATION_DAYS, 7)
    CACHE_FILE_DIR = Path(__file__).parent.parent.parent / "cache"
    CACHE_FILE_NAME = "coordinate.msgpack"
    CACHE_FILE_PATH = CACHE_FILE_DIR / CACHE_FILE_NAME

    def __init__(self):
        self.date = datetime.now()

        try:
            os.makedirs(self.CACHE_FILE_DIR, exist_ok=True)
        except Exception as e:
            logger.error(
                f"Error creating cache directory {self.CACHE_FILE_DIR}: {e}", exc_info=True
            )
            raise

        self.cache: list[CoordinateEntry] = list()
        self.load_cache()
        self.clean()

    @staticmethod
    def _entry_to_data(entry: CoordinateEntry) -> dict:
        return {
            "poi": {
                "country": entry.poi.country,
                "state": entry.poi.state,
                "city": entry.poi.city,
                "institution": entry.poi.institution,
            },
            "coordinate": {
                "latitude": entry.coordinate.latitude,
                "longitude": entry.coordinate.longitude,
            },
            "timestamp": entry.timestamp.isoformat(),
        }

    @staticmethod
    def _data_to_entry(data: dict) -> CoordinateEntry | None:
        try:
            poi_data = data.get("poi", {})
            coord_data = data.get("coordinate", {})
            timestamp_raw = data.get("timestamp")
            if timestamp_raw is None:
                return None

            timestamp = datetime.fromisoformat(timestamp_raw)
            poi = NewsPOI(
                country=poi_data.get("country"),
                state=poi_data.get("state"),
                city=poi_data.get("city"),
                institution=poi_data.get("institution"),
            )
            coordinate = NewsCoordinate(
                latitude=coord_data.get("latitude"),
                longitude=coord_data.get("longitude"),
            )
            return CoordinateEntry(poi, coordinate, timestamp)
        except Exception as e:
            logger.debug(f"Skipping invalid cache entry: {data} ({e})")
            return None

    def load_cache(self) -> None:
        if not self.CACHE_FILE_PATH.exists():
            return

        try:
            with open(self.CACHE_FILE_PATH, "rb") as f:
                packed_cache = msgpack.unpack(f, raw=False)

            if not isinstance(packed_cache, list):
                raise ValueError("Invalid cache format: expected list")

            for item in packed_cache:
                entry = self._data_to_entry(
                    item if isinstance(item, dict) else {})
                if entry:
                    self.cache.append(entry)

            logger.info(
                f"Loaded coordinate cache with {len(self.cache)} entries from {self.CACHE_FILE_PATH}"
            )
        except Exception as e:
            logger.error(
                f"Error loading coordinate cache: {e}", exc_info=True
            )
            self.cache = list()

    def save_cache(self) -> None:
        try:
            data = [self._entry_to_data(entry) for entry in self.cache]
            with open(self.CACHE_FILE_PATH, "wb") as f:
                msgpack.pack(data, f, use_bin_type=True)
            logger.info(
                f"Saved coordinate cache with {len(self.cache)} entries to {self.CACHE_FILE_PATH}"
            )
        except Exception as e:
            logger.error(
                f"Error saving coordinate cache to {self.CACHE_FILE_PATH}: {e}", exc_info=True
            )

    def clean(self) -> None:
        if not self.cache:
            return

        logger.info("Cleaning expired coordinate cache...")
        expire_threshold = datetime.now() - timedelta(days=self.EXPIRATION_DAYS)
        original_count = len(self.cache)
        self.cache = [
            entry for entry in self.cache
            if entry and entry.timestamp >= expire_threshold
        ]
        cleaned_count = original_count - len(self.cache)

        if cleaned_count > 0:
            logger.info(
                f"Cleaned {cleaned_count} expired entries from coordinate cache"
            )
            self.save_cache()
        else:
            logger.info("No expired entries found in coordinate cache")

    def insert_entry(self, entry: CoordinateEntry, force_refresh: bool) -> None:
        if not entry:
            logger.warning(
                f"Attempted to insert invalid coordinate entry for POI {str(entry.poi)}, skipping"
            )
            return
        if entry in self.cache:
            if not force_refresh:
                logger.debug(
                    f"Coordinate entry for POI {str(entry)} already exists in cache, skipping insert"
                )
                return
            else:
                logger.debug(
                    f"Force refreshing coordinate entry for POI {str(entry)}, removing old entry"
                )
                self.cache = [e for e in self.cache if e != entry]
                self.cache.append(entry)
                self.save_cache()

        self.cache.append(entry)
        logger.debug(
            f"Inserted new coordinate entry for POI {str(entry)} into cache"
        )
        self.save_cache()

    def select_coordinate(self, poi: NewsPOI) -> NewsCoordinate | None:
        if not poi:
            return None
        for entry in self.cache:
            if entry.poi == poi:
                logger.debug(
                    f"Cache hit for POI {str(poi)}, returning cached coordinates"
                )
                return copy.deepcopy(entry.coordinate)
        logger.debug(f"Cache miss for POI {str(poi)}")
        return None


cache_manager = CoordinateCacheManager()
