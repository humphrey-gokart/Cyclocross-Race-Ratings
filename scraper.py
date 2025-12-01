#!/usr/bin/env python3
"""
CX Race Ratings Scraper
Scrapes cyclocross results and calculates excitement ratings.
Uses ScraperAPI to handle anti-bot measures.

Setup:
1. Sign up at https://www.scraperapi.com/ (free tier: 1000 requests/month)
2. Add your API key as a GitHub secret: SCRAPER_API_KEY
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime
from pathlib import Path
import time

# ScraperAPI config - get free key at scraperapi.com
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")
SCRAPER_API_URL = "http://api.scraperapi.com"

# Direct requests as fallback
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Cyclocross24 race configurations
# To add new races: visit cyclocross24.com, find the race, get ID from URL (/race/XXXXX/)
CYCLOCROSS24_RACES = [
    # World Cup 2025-26
    {"id": 17817, "series": "UCI World Cup", "venue": "Tábor", "country": "CZE", "date": "2025-11-23", "category": "Elite Men"},
    {"id": 17816, "series": "UCI World Cup", "venue": "Tábor", "country": "CZE", "date": "2025-11-23", "category": "Elite Women"},
    {"id": 17826, "series": "UCI World Cup", "venue": "Flamanville", "country": "FRA", "date": "2025-11-30", "category": "Elite Men"},
    {"id": 17825, "series": "UCI World Cup", "venue": "Flamanville", "country": "FRA", "date": "2025-11-30", "category": "Elite Women"},
    
    # European Championships
    {"id": 17721, "series": "European Championships", "venue": "Middelkerke", "country": "BEL", "date": "2025-11-09", "category": "Elite Men"},
    {"id": 17712, "series": "European Championships", "venue": "Middelkerke", "country": "BEL", "date": "2025-11-08", "category": "Elite Women"},
    
    # Superprestige
    {"id": 17660, "series": "Superprestige", "venue": "Ruddervoorde", "country": "BEL", "date": "2025-10-12", "category": "Elite Men"},
    {"id": 17659, "series": "Superprestige", "venue": "Ruddervoorde", "country": "BEL", "date": "2025-10-12", "category": "Elite Women"},
    {"id": 17734, "series": "Superprestige", "venue": "Overijse", "country": "BEL", "date": "2025-11-02", "category": "Elite Men"},
    {"id": 17733, "series": "Superprestige", "venue": "Overijse", "country": "BEL", "date": "2025-11-02", "category": "Elite Women"},
    {"id": 17741, "series": "Superprestige", "venue": "Niel", "country": "BEL", "date": "2025-11-11", "category": "Elite Men"},
    {"id": 17740, "series": "Superprestige", "venue": "Niel", "country": "BEL", "date": "2025-11-11", "category": "Elite Women"},
    {"id": 17796, "series": "Superprestige", "venue": "Merksplas", "country": "BEL", "date": "2025-11-22", "category": "Elite Men"},
    {"id": 17795, "series": "Superprestige", "venue": "Merksplas", "country": "BEL", "date": "2025-11-22", "category": "Elite Women"},
    
    # X2O Trofee
    {"id": 17687, "series": "X2O Trofee", "venue": "Koppenberg", "country": "BEL", "date": "2025-11-01", "category": "Elite Men"},
    {"id": 17686, "series": "X2O Trofee", "venue": "Koppenberg", "country": "BEL", "date": "2025-11-01", "category": "Elite Women"},
    {"id": 17706, "series": "X2O Trofee", "venue": "Lokeren", "country": "BEL", "date": "2025-11-02", "category": "Elite Men"},
    {"id": 17705, "series": "X2O Trofee", "venue": "Lokeren", "country": "BEL", "date": "2025-11-02", "category": "Elite Women"},
    {"id": 17780, "series": "X2O Trofee", "venue": "Hamme", "country": "BEL", "date": "2025-11-15", "category": "Elite Men"},
    {"id": 17779, "series": "X2O Trofee", "venue": "Hamme", "country": "BEL", "date": "2025-11-15", "category": "Elite Women"},
]


def fetch_url(url: str) -> str | None:
    """Fetch URL using ScraperAPI if available, otherwise direct request."""
    try:
        if SCRAPER_API_KEY:
            # Use ScraperAPI
            params = {
                "api_key": SCRAPER_API_KEY,
                "url": url,
            }
            response = requests.get(SCRAPER_API_URL, params=params, timeout=60)
        else:
            # Direct request (may get blocked)
            print("  Warning: No SCRAPER_API_KEY set, using direct request")
            response = requests.get(url, headers=HEADERS, timeout=30)
        
        response.raise_for_status()
        return response.text
    
    except requests.RequestException as e:
        print(f"  Failed to fetch {url}: {e}")
        return None


def parse_time_gap(gap_str: str) -> int:
    """Parse time gap string to seconds. Returns 0 for same time."""
    if not gap_str:
        return 0
    
    gap_str = gap_str.strip()
    
    # Same time indicators
    if gap_str.lower() in ["", "-", "s.t.", "st", '""', ",,", "0"]:
        return 0
    
    # Remove leading + and whitespace
    gap_str = gap_str.lstrip("+").strip()
    
    # Handle MM:SS or M:SS format (e.g., "0:15", "1:23")
    if ":" in gap_str:
        parts = gap_str.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            pass
    
    # Handle just seconds
    try:
        return int(gap_str)
    except ValueError:
        pass
    
    return 0


def calculate_rating(gaps: list[int]) -> int:
    """
    Calculate excitement rating (1-5 stars) based on time gaps.
    
    Sprint finishes = 5 stars
    Close finishes (<10s) = 4-5 stars
    Medium gaps (10-30s) = 3 stars  
    Large gaps (30-60s) = 2 stars
    Dominant wins (>60s) = 1 star
    """
    if len(gaps) < 2:
        return 3  # Default if not enough data
    
    gap_to_2nd = gaps[0] if gaps else 999
    gap_to_3rd = gaps[1] if len(gaps) > 1 else 999
    
    # Count riders within 10 seconds of winner
    close_finishers = sum(1 for g in gaps[:10] if g <= 10)
    
    score = 0
    
    # Gap to 2nd place (0-40 points) - most important
    if gap_to_2nd == 0:  # Sprint finish
        score += 40
    elif gap_to_2nd <= 3:
        score += 35
    elif gap_to_2nd <= 10:
        score += 25
    elif gap_to_2nd <= 20:
        score += 15
    elif gap_to_2nd <= 30:
        score += 10
    elif gap_to_2nd <= 60:
        score += 5
    
    # Gap to 3rd place (0-30 points)
    if gap_to_3rd <= 5:
        score += 30
    elif gap_to_3rd <= 15:
        score += 20
    elif gap_to_3rd <= 30:
        score += 10
    elif gap_to_3rd <= 60:
        score += 5
    
    # Close finishers bonus (0-30 points)
    score += min(close_finishers * 6, 30)
    
    # Convert to 1-5 stars
    if score >= 80:
        return 5
    elif score >= 60:
        return 4
    elif score >= 40:
        return 3
    elif score >= 20:
        return 2
    else:
        return 1


def scrape_cyclocross24(race_id: int) -> list[int] | None:
    """Scrape time gaps from cyclocross24.com race page."""
    url = f"https://cyclocross24.com/race/{race_id}/"
    
    time.sleep(1)  # Rate limiting
    html = fetch_url(url)
    
    if not html:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    gaps = []
    
    # Find result table - cyclocross24 uses various table structures
    # Look for rows with position numbers and time data
    tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:16]:  # Skip header, get top 15
            cells = row.find_all("td")
            if len(cells) >= 3:
                # Look for time gap in cells
                for cell in cells:
                    text = cell.get_text(strip=True)
                    # Match time patterns: "0:15", "s.t.", numbers, or winner time like "58:40"
                    if re.match(r"^(\d{1,2}:\d{2}|\d+|s\.t\.)$", text, re.IGNORECASE):
                        gap = parse_time_gap(text)
                        # Ignore winner's race time (>50 mins = 3000s)
                        if gap < 3000:
                            gaps.append(gap)
                        break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_gaps = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            unique_gaps.append(g)
    
    return unique_gaps if unique_gaps else None


def scrape_all_races() -> list[dict]:
    """Scrape all configured races."""
    results = []
    
    for race in CYCLOCROSS24_RACES:
        print(f"Scraping {race['venue']} ({race['category']})...")
        gaps = scrape_cyclocross24(race["id"])
        
        if gaps:
            rating = calculate_rating(gaps)
            entry = {
                "date": race["date"],
                "venue": race["venue"],
                "country": race["country"],
                "series": race["series"],
                "category": race["category"],
                "rating": rating
            }
            results.append(entry)
            gaps_preview = gaps[:5]
            print(f"  ✓ Rating: {rating} stars (gaps: {gaps_preview})")
        else:
            print(f"  - No results found (race may not have happened yet)")
    
    return results


def update_races_json(output_path: str = "races.json"):
    """Update the races.json file with fresh data."""
    # Load existing data
    existing = {"races": [], "lastUpdated": ""}
    if Path(output_path).exists():
        with open(output_path) as f:
            existing = json.load(f)
    
    # Create lookup of existing races
    existing_keys = {
        (r["date"], r["venue"], r["category"]): r 
        for r in existing.get("races", [])
    }
    
    # Scrape new data
    new_races = scrape_all_races()
    
    # Merge (new data takes precedence)
    for race in new_races:
        key = (race["date"], race["venue"], race["category"])
        existing_keys[key] = race
    
    # Sort by date descending
    all_races = sorted(existing_keys.values(), key=lambda x: x["date"], reverse=True)
    
    # Save
    output = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "races": all_races
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Saved {len(all_races)} races to {output_path}")


if __name__ == "__main__":
    if not SCRAPER_API_KEY:
        print("=" * 60)
        print("TIP: Set SCRAPER_API_KEY environment variable for reliable scraping")
        print("Get a free key at: https://www.scraperapi.com/")
        print("=" * 60)
        print()
    
    update_races_json()
