#!/usr/bin/env python3
"""
CX Race Ratings Scraper
Uses the official Cyclocross24 JSON API instead of scraping HTML
"""

import requests
import json
from datetime import datetime
import time

BASE = "https://cyclocross24.com/api/2"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# Series we care about
TRACKED_SERIES = [
    "UCI World Cup",
    "Superprestige",
    "X2O Trofee",
    "X2O Badkamers Trofee",
    "Exact Cross",
    "European Championships",
    "World Championships",
    "Koppenbergcross",
    "Azencross",
    "GP Sven Nys",
    "Druivencross",
]

TRACKED_CATEGORIES = ["Elite Men", "Elite Women", "Men Elite", "Women Elite"]


def calculate_rating(gaps: list[int]) -> int:
    """Calculate rating using same logic as before."""
    if len(gaps) < 2:
        return 3

    gap_to_2nd = gaps[0] if gaps else 999
    gap_to_3rd = gaps[1] if len(gaps) > 1 else 999
    close_finishers = sum(1 for g in gaps[:10] if g <= 10)

    score = 0

    if gap_to_2nd == 0: score += 40
    elif gap_to_2nd <= 3: score += 35
    elif gap_to_2nd <= 10: score += 25
    elif gap_to_2nd <= 20: score += 15
    elif gap_to_2nd <= 30: score += 10
    elif gap_to_2nd <= 60: score += 5

    if gap_to_3rd <= 5: score += 30
    elif gap_to_3rd <= 15: score += 20
    elif gap_to_3rd <= 30: score += 10
    elif gap_to_3rd <= 60: score += 5

    score += min(close_finishers * 6, 30)

    if score >= 80: return 5
    elif score >= 60: return 4
    elif score >= 40: return 3
    elif score >= 20: return 2
    else: return 1


def get_recent_races():
    """Get list of races from API."""
    races = []
    url = f"{BASE}/race/?format=json"

    while url:
        print(f"Fetching: {url}")
        r = requests.get(url, headers=HEADERS, timeout=30)
        data = r.json()

        for race in data["results"]:
            races.append(race)

        url = data.get("next")

    print(f"✓ Found {len(races)} total races")
    return races


def scrape_race(race):
    """Scrape rating & metadata from API race object."""

    race_id = race["id"]
    race_name = race.get("name", "").strip()
    series = race.get("competition", "").strip()
    category = race.get("category", "").strip()
    date = race.get("date", "")
    venue = race.get("location", "")
    country = race.get("country", "")

    # Filter — only tracked series + elite
    if series not in TRACKED_SERIES:
        return None

    if category not in TRACKED_CATEGORIES:
        return None

    print(f"  Analyzing race {race_id}: {race_name} — {category}")

    # get results
    url = f"{BASE}/results/?format=json&race={race_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    data = r.json()

    gaps = []

    for row in data["results"]:
        rider_gap = row.get("timeGapValue")

        if rider_gap is None:
            continue

        try:
            gap_seconds = int(rider_gap)
            gaps.append(gap_seconds)
        except:
            pass

    if len(gaps) < 2:
        return None

    rating = calculate_rating(gaps)

    return {
        "date": date,
        "venue": venue,
        "country": country,
        "series": series,
        "category": category,
        "rating": rating
    }


def update_races_json(output_path="races.json"):
    print("===== CX RACE RATINGS UPDATE =====")
    races = get_recent_races()

    results = []

    for race in races:
        r = scrape_race(race)
        if r:
            results.append(r)

    sorted_races = sorted(results, key=lambda x: x["date"], reverse=True)

    data = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "races": sorted_races
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Saved {len(sorted_races)} races to {output_path}")


if __name__ == "__main__":
    update_races_json()
