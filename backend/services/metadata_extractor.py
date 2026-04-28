import json
import logging
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Tuple

from PIL import Image
from PIL.ExifTags import TAGS

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CACHE_DIR = _PROJECT_ROOT / "backend" / "data"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_DB = _CACHE_DIR / "geocache.db"

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_NOMINATIM_HEADERS = {"User-Agent": "GeminiPhotoSearch/0.1.0"}

_last_nominatim_call = 0.0
_lock = threading.Lock()


def _init_cache() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_CACHE_DB))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS geocache (
            lat_round TEXT NOT NULL,
            lon_round TEXT NOT NULL,
            display_name TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (lat_round, lon_round)
        )
        """
    )
    conn.commit()
    return conn


def _get_cached_location(lat: float, lon: float) -> str | None:
    lat_r = f"{lat:.3f}"
    lon_r = f"{lon:.3f}"
    conn = _init_cache()
    try:
        row = conn.execute(
            "SELECT display_name FROM geocache WHERE lat_round = ? AND lon_round = ?",
            (lat_r, lon_r),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _cache_location(lat: float, lon: float, display_name: str) -> None:
    lat_r = f"{lat:.3f}"
    lon_r = f"{lon:.3f}"
    conn = _init_cache()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO geocache (lat_round, lon_round, display_name, fetched_at)
            VALUES (?, ?, ?, ?)
            """,
            (lat_r, lon_r, display_name, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _fetch_nominatim(lat: float, lon: float) -> str | None:
    url = f"{_NOMINATIM_URL}?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
    req = urllib.request.Request(url, headers=_NOMINATIM_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            display_name = data.get("display_name")
            if display_name:
                logger.info(f"Geocoded ({lat}, {lon}) -> {display_name}")
                return display_name
    except urllib.error.HTTPError as e:
        logger.warning(f"Nominatim HTTP error {e.code} for ({lat}, {lon})")
    except Exception as e:
        logger.warning(f"Nominatim call failed for ({lat}, {lon}): {e}")
    return None


def _rate_limited_fetch_nominatim(lat: float, lon: float) -> str | None:
    """Fetch from Nominatim while respecting the 1 req/sec rate limit."""
    global _last_nominatim_call
    with _lock:
        elapsed = time.time() - _last_nominatim_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        display_name = _fetch_nominatim(lat, lon)
        _last_nominatim_call = time.time()
        return display_name


def _dms_to_dd(dms, ref: str) -> float:
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]
    dd = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if ref in ("S", "W"):
        dd = -dd
    return dd


def extract_gps(exif_data: dict) -> Tuple[float, float] | None:
    gps_info = exif_data.get("GPSInfo")
    if not gps_info:
        return None
    try:
        lat_dms = gps_info.get(2)
        lat_ref = gps_info.get(1)
        lon_dms = gps_info.get(4)
        lon_ref = gps_info.get(3)
        if lat_dms and lat_ref and lon_dms and lon_ref:
            lat = _dms_to_dd(lat_dms, lat_ref)
            lon = _dms_to_dd(lon_dms, lon_ref)
            return (lat, lon)
    except Exception:
        pass
    return None


def extract_date_taken(exif_data: dict) -> str | None:
    date_tags = (36867, 306)
    for tag in date_tags:
        val = exif_data.get(tag)
        if val:
            try:
                dt = datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
                return dt.isoformat()
            except ValueError:
                continue
    return None


def extract_metadata(image_path: Path) -> dict:
    result = {
        "date_taken": None,
        "lat": None,
        "lon": None,
        "location": None,
    }
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return result
            raw_data = {tag: value for tag, value in exif.items()}

            date_taken = extract_date_taken(raw_data)
            if date_taken:
                result["date_taken"] = date_taken

            gps = extract_gps(raw_data)
            if gps:
                lat, lon = gps
                result["lat"] = lat
                result["lon"] = lon
                cached = _get_cached_location(lat, lon)
                if cached:
                    result["location"] = cached
                else:
                    display_name = _rate_limited_fetch_nominatim(lat, lon)
                    if display_name:
                        _cache_location(lat, lon, display_name)
                        result["location"] = display_name
    except Exception as e:
        logger.warning(f"EXIF extraction failed for {image_path}: {e}")
    return result
