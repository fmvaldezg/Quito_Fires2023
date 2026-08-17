#!/usr/bin/env python3
"""Fetch recent VIIRS NRT fire detections from NASA FIRMS, merge them with
the committed dataset, trim to a rolling window, and write back."""

import csv
import io
import json
import os
import sys
import time
from datetime import date, timedelta

import requests

MAP_KEY_ENV = "FIRMS_MAP_KEY"
SOURCE = "VIIRS_SNPP_NRT"
BBOX = "-81.5,-5.1,-75.0,1.5"  # west,south,east,north - whole Ecuador
DAY_RANGE = 5  # max allowed for VIIRS_SNPP_NRT - do not raise past that
ROLLING_WINDOW_DAYS = 90
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output_file.json")

MAX_FETCH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5  # multiplied by attempt number between retries

# FIRMS CSV column -> GeoJSON property name, to match index.html's paint
# expressions which were written against the old archive-download schema.
FIELD_MAP = {
    "bright_ti4": "brightness",
    "bright_ti5": "bright_t31",
}

NUMERIC_FIELDS = {"latitude", "longitude", "brightness", "bright_t31", "frp", "scan", "track"}


def fetch_csv_rows(map_key: str) -> list[dict]:
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{SOURCE}/{BBOX}/{DAY_RANGE}"

    last_error = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return list(csv.DictReader(io.StringIO(response.text)))
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < MAX_FETCH_ATTEMPTS:
                wait = RETRY_BACKOFF_SECONDS * attempt
                print(f"fetch attempt {attempt} failed ({exc}); retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)

    raise last_error


def row_to_feature(row: dict) -> dict:
    props = {}
    for key, value in row.items():
        key = FIELD_MAP.get(key, key)
        if key in NUMERIC_FIELDS:
            value = float(value)
        props[key] = value
    props["acq_time"] = str(row["acq_time"]).zfill(4)
    props["instrument"] = "VIIRS"

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [props["longitude"], props["latitude"]],
        },
        "properties": props,
    }


def load_existing(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)["features"]


def dedup_key(props: dict) -> tuple:
    return (
        round(props["latitude"], 4),
        round(props["longitude"], 4),
        props["acq_date"],
        props["acq_time"],
        props["satellite"],
    )


def merge_trim_sort(existing: list, new: list, window_days: int) -> list:
    by_key = {}
    for feature in existing + new:
        by_key[dedup_key(feature["properties"])] = feature

    cutoff = (date.today() - timedelta(days=window_days)).isoformat()
    kept = [f for f in by_key.values() if f["properties"]["acq_date"] >= cutoff]
    kept.sort(key=lambda f: (f["properties"]["acq_date"], f["properties"]["acq_time"]))
    return kept


def main():
    map_key = os.environ.get(MAP_KEY_ENV)
    if not map_key:
        sys.exit(f"{MAP_KEY_ENV} environment variable is not set")

    rows = fetch_csv_rows(map_key)
    new_features = [row_to_feature(row) for row in rows]

    existing_features = load_existing(OUTPUT_PATH)
    merged = merge_trim_sort(existing_features, new_features, ROLLING_WINDOW_DAYS)

    with open(OUTPUT_PATH, "w") as f:
        json.dump({"type": "FeatureCollection", "features": merged}, f)

    dates = sorted({f["properties"]["acq_date"] for f in merged})
    date_range = f"{dates[0]} to {dates[-1]}" if dates else "no data"
    print(
        f"fetched={len(new_features)} existing={len(existing_features)} "
        f"merged_total={len(merged)} date_range={date_range}"
    )


if __name__ == "__main__":
    main()
