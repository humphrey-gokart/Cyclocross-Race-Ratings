#!/usr/bin/env python3
"""
CX Race Ratings Scraper
Automatically discovers and scrapes cyclocross results, calculates excitement ratings.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from pathlib import Path
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Series we care about (filters out small local races)
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

# Categories we want
TRACKED_CATEGORIES = ["Elite Men", "Elite Women", "Men Elite", "Women Elite"]


def parse_time_gap(gap_str: str) -> int:
    """Parse time gap string to seconds. Returns 0 for same time."""
    if not gap_str:
        return 0
    
    gap_str = gap_str.strip()
    
    if gap_str.lower() in ["", "-", "s.t.", "st", '""', ",,", "0"]:
        return 0
    
    gap_str = gap_str.lstrip("+").strip()
    
    if ":" in gap_str:
        parts = gap_str.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            pass
    
    try:
        return int(gap_str)
    except ValueError:
        pass
    
    return 0


def calculate_rating(gaps: list[int]) -> int:
    """Calculate excitement rating (1-5 stars) based on time gaps."""
    if len(gaps) < 2:
        return 3
    
    gap_to_2nd = gaps[0] if gaps else 999
    gap_to_3rd = gaps[1] if len(gaps) > 1 else 999
    close_finishers = sum(1 for g in gaps[:10] if g <= 10)
    
    score = 0
    
    if gap_to_2nd == 0:
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
    
    if gap_to_3rd <= 5:
        score += 30
    elif gap_to_3rd <= 15:
        score += 20
    elif gap_to_3rd <= 30:
        score += 10
    elif gap_to_3rd <= 60:
        score += 5
    
    score += min(close_finishers * 6, 30)
    
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


def discover_races() -> list[dict]:
    """Discover recent races from cyclocross24 homepage."""
    print("Discovering races from cyclocross24.com...")
    
    try:
        response = requests.get("https://cyclocross24.com/", headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch homepage: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    race_links = soup.find_all("a", href=re.compile(r"/race/\d+/"))
    
    races = []
    seen_ids = set()
    
    for link in race_links:
        match = re.search(r"/race/(\d+)/", link.get("href", ""))
        if match:
            race_id = match.group(1)
            if race_id not in seen_ids:
                seen_ids.add(race_id)
                races.append({"id": race_id})
    
    print(f"  Found {len(races)} race IDs")
    return races


def scrape_race(race_id: str) -> dict | None:
    """Scrape a single race page for metadata and results."""
    url = f"https://cyclocross24.com/race/{race_id}/"
    
    try:
        time.sleep(1.5)
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Failed to fetch race {race_id}: {e}")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Try to extract race info from page title or headers
    title = soup.find("title")
    title_text = title.get_text() if title else ""
    
    # Look for h1/h2 headers for race name
    header = soup.find(["h1", "h2"])
    header_text = header.get_text(strip=True) if header else ""
    
    # Determine series
    series = None
    combined_text = f"{title_text} {header_text}".lower()
    
    for s in TRACKED_SERIES:
        if s.lower() in combined_text:
            series = s
            break
    
    if not series:
        # Check for common patterns
        if "world cup" in combined_text or "cdm" in combined_text:
            series = "UCI World Cup"
        elif "superprestige" in combined_text:
            series = "Superprestige"
        elif "x2o" in combined_text or "trofee" in combined_text:
            series = "X2O Trofee"
        elif "european" in combined_text and "champion" in combined_text:
            series = "European Championships"
        elif "world" in combined_text and "champion" in combined_text:
            series = "World Championships"
    
    if not series:
        return None  # Skip races we don't track
    
    # Determine category from URL or page content
    category = None
    if "elite" in combined_text and "men" in combined_text and "women" not in combined_text:
        category = "Elite Men"
    elif "elite" in combined_text and "women" in combined_text:
        category = "Elite Women"
    elif "men elite" in combined_text:
        category = "Elite Men"
    elif "women elite" in combined_text:
        category = "Elite Women"
    
    if not category:
        return None  # Skip non-elite categories
    
    # Extract venue from title (usually format: "Race Name Venue Year")
    venue = header_text.split("-")[0].strip() if "-" in header_text else header_text
    venue = re.sub(r'\d{4}', '', venue).strip()  # Remove year
    venue = venue.replace("Results", "").replace("Cyclocross", "").strip()
    if len(venue) > 30:
        venue = venue[:30]
    
    # Try to find date
    date_match = re.search(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', response.text, re.IGNORECASE)
    if date_match:
        try:
            date_str = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}"
            date_obj = datetime.strptime(date_str, "%d %B %Y")
            race_date = date_obj.strftime("%Y-%m-%d")
        except:
            race_date = datetime.now().strftime("%Y-%m-%d")
    else:
        race_date = datetime.now().strftime("%Y-%m-%d")
    
    # Extract time gaps from results table
    gaps = []
    tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:16]:
            cells = row.find_all("td")
            if len(cells) >= 3:
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if re.match(r"^(\d{1,2}:\d{2}|\d+|s\.t\.)$", text, re.IGNORECASE):
                        gap = parse_time_gap(text)
                        if gap < 3000:
                            gaps.append(gap)
                        break
    
    if not gaps:
        return None
    
    # Remove duplicates
    seen = set()
    unique_gaps = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            unique_gaps.append(g)
    
    if len(unique_gaps) < 2:
        return None
    
    rating = calculate_rating(unique_gaps)
    
    return {
        "date": race_date,
        "venue": venue if venue else f"Race {race_id}",
        "country": "",
        "series": series,
        "category": category,
        "rating": rating,
        "gaps": unique_gaps[:5]
    }


def scrape_all_races() -> list[dict]:
    """Discover and scrape all recent races."""
    races = discover_races()
    results = []
    
    for race in races[:50]:  # Limit to 50 most recent
        print(f"Checking race {race['id']}...")
        result = scrape_race(race["id"])
        
        if result:
            print(f"  ✓ {result['venue']} ({result['category']}): {result['rating']} stars")
            # Remove gaps from final output
            del result["gaps"]
            results.append(result)
    
    return results


def update_races_json(output_path: str = "races.json"):
    """Update the races.json file with fresh data."""
    existing = {"races": [], "lastUpdated": ""}
    if Path(output_path).exists():
        with open(output_path) as f:
            existing = json.load(f)
    
    existing_keys = {
        (r["date"], r["venue"], r["category"]): r 
        for r in existing.get("races", [])
    }
    
    new_races = scrape_all_races()
    
    for race in new_races:
        key = (race["date"], race["venue"], race["category"])
        existing_keys[key] = race
    
    all_races = sorted(existing_keys.values(), key=lambda x: x["date"], reverse=True)
    
    output = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "races": all_races
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Saved {len(all_races)} races to {output_path}")


if __name__ == "__main__":
    update_races_json()
