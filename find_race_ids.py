#!/usr/bin/env python3
"""
Helper script to find cyclocross24.com race IDs.
Run this to discover race IDs for adding to the scraper.

Usage: 
  export SCRAPER_API_KEY=your_key  # optional but recommended
  python find_race_ids.py
"""

import requests
from bs4 import BeautifulSoup
import re
import os

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")
SCRAPER_API_URL = "http://api.scraperapi.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch_url(url: str) -> str | None:
    """Fetch URL using ScraperAPI if available."""
    try:
        if SCRAPER_API_KEY:
            params = {"api_key": SCRAPER_API_KEY, "url": url}
            response = requests.get(SCRAPER_API_URL, params=params, timeout=60)
        else:
            response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch: {e}")
        return None


def find_recent_races():
    """Scrape the cyclocross24 homepage to find recent race IDs."""
    print("Fetching cyclocross24.com...")
    html = fetch_url("https://cyclocross24.com/")
    
    if not html:
        return
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Find all race links
    race_links = soup.find_all("a", href=re.compile(r"/race/\d+/"))
    
    seen = set()
    print("\nRecent races found on cyclocross24.com:\n")
    print(f"{'ID':<8} {'URL':<50}")
    print("-" * 60)
    
    for link in race_links:
        href = link.get("href", "")
        match = re.search(r"/race/(\d+)/", href)
        if match:
            race_id = match.group(1)
            if race_id not in seen:
                seen.add(race_id)
                full_url = f"https://cyclocross24.com/race/{race_id}/"
                print(f"{race_id:<8} {full_url}")


if __name__ == "__main__":
    print("=" * 60)
    print("Cyclocross24 Race ID Finder")
    print("=" * 60)
    
    if not SCRAPER_API_KEY:
        print("\nTIP: Set SCRAPER_API_KEY for reliable fetching")
        print("     export SCRAPER_API_KEY=your_key")
    
    print()
    find_recent_races()
    print()
    print("To add a race to the scraper:")
    print("1. Find the race ID from above")
    print("2. Add to CYCLOCROSS24_RACES in scraper.py:")
    print('   {"id": 17817, "series": "UCI World Cup", "venue": "Tábor", ...}')
