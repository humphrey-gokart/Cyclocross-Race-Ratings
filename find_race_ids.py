#!/usr/bin/env python3
"""
Helper to find cyclocross24.com race IDs.
Usage: python find_race_ids.py
"""

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}


def find_recent_races():
    """Find recent race IDs from cyclocross24 homepage."""
    print("Fetching cyclocross24.com...")
    
    try:
        response = requests.get("https://cyclocross24.com/", headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed: {e}")
        return
    
    soup = BeautifulSoup(response.text, "html.parser")
    race_links = soup.find_all("a", href=re.compile(r"/race/\d+/"))
    
    seen = set()
    print("\nRecent races:\n")
    
    for link in race_links:
        match = re.search(r"/race/(\d+)/", link.get("href", ""))
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            print(f"  ID: {match.group(1)}  →  https://cyclocross24.com/race/{match.group(1)}/")


if __name__ == "__main__":
    find_recent_races()
    print("\nAdd races to CYCLOCROSS24_RACES in scraper.py")
