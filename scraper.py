#!/usr/bin/env python3
"""
Cyclocross Race Ratings Scraper
Uses parse.bot APIs to fetch race data from cyclocross24.com
"""

import requests
import json
import os
from datetime import datetime

# Parse.bot API endpoints
EVENTS_API = "https://api.parse.bot/scraper/a255becf-6539-415f-ae48-a14613ebe19a/get_race_event_list"
RESULTS_API = "https://api.parse.bot/scraper/55aa208f-d53a-4bfc-bbb7-1c3681595d23/get_race_results"

# Series we care about
TARGET_SERIES = [
    "UCI World Cup",
    "World Cup",
    "Superprestige",
    "X2O Trofee",
    "X2O",
    "Exact Cross",
    "European Championships",
    "World Championships",
    "National Championships",
]


def parse_time_to_seconds(time_str):
    """Convert time string to seconds. Returns None if invalid."""
    if not time_str:
        return None
    
    time_str = str(time_str).strip()
    
    # Handle "s.t." (same time)
    if time_str.lower() in ["s.t.", "st", "s.t"]:
        return 0
    
    try:
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) == 2:
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        else:
            return int(float(time_str))
    except (ValueError, TypeError):
        return None


def calculate_rating(results):
    """
    Calculate excitement rating based on time gaps.
    Returns a tuple of (score, stars).
    """
    if not results or len(results) < 2:
        return 0, 1
    
    # Sort by position
    sorted_results = sorted(results, key=lambda x: x.get("position", 999))
    
    # Extract gaps - position 1 has finish time, others have gaps
    gaps = []
    
    for result in sorted_results:
        pos = result.get("position")
        time_str = result.get("Time") or result.get("time")
        
        if not time_str:
            continue
            
        seconds = parse_time_to_seconds(time_str)
        
        if seconds is None:
            continue
        
        if pos == 1:
            # Winner's time - skip (it's finish time, not gap)
            continue
        else:
            # For position 2+, the Time field is the gap
            gaps.append(seconds)
    
    gap_to_2nd = gaps[0] if len(gaps) > 0 else None
    gap_to_3rd = gaps[1] if len(gaps) > 1 else None
    
    # Count riders within 10 seconds
    close_finishers = sum(1 for g in gaps if g <= 10) + 1  # +1 for winner
    
    # Calculate score
    score = 0
    
    # Gap to 2nd (0-40 points) - most important
    if gap_to_2nd is not None:
        if gap_to_2nd == 0:
            score += 40  # Same time / sprint finish
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
    
    # Gap to 3rd (0-30 points)
    if gap_to_3rd is not None:
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
    
    # Convert to stars
    if score >= 80:
        stars = 5
    elif score >= 60:
        stars = 4
    elif score >= 40:
        stars = 3
    elif score >= 20:
        stars = 2
    else:
        stars = 1
    
    return score, stars


def matches_target_series(series_name):
    """Check if the series matches our targets."""
    if not series_name:
        return False
    series_lower = series_name.lower()
    for target in TARGET_SERIES:
        if target.lower() in series_lower:
            return True
    return False


def get_race_events():
    """Fetch list of race events from parse.bot API."""
    print("Fetching race events...")
    try:
        response = requests.post(EVENTS_API, json={}, timeout=30)
        response.raise_for_status()
        data = response.json()
        events = data.get("events", [])
        print(f"Found {len(events)} total events")
        return events
    except Exception as e:
        print(f"Error fetching events: {e}")
        return []


def get_race_results(event_id):
    """Fetch results for a specific race from parse.bot API."""
    try:
        response = requests.post(
            RESULTS_API,
            json={"event_id": event_id},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Check we have categories
        categories = data.get("categories", [])
        if categories and len(categories) > 0:
            return data
        
        return None
    except Exception as e:
        print(f"  Error fetching results for {event_id}: {e}")
        return None


def load_existing_races():
    """Load existing races.json if it exists."""
    if os.path.exists("races.json"):
        try:
            with open("races.json", "r") as f:
                data = json.load(f)
                # Ensure it's a list of dictionaries
                if isinstance(data, list) and all(isinstance(r, dict) for r in data):
                    return data
                else:
                    print("Warning: races.json has invalid format, starting fresh")
                    return []
        except Exception as e:
            print(f"Warning: Could not load races.json: {e}")
            pass
    return []


def save_races(races):
    """Save races to races.json."""
    with open("races.json", "w") as f:
        json.dump(races, f, indent=2)
    print(f"Saved {len(races)} races to races.json")


def extract_category_from_title(title):
    """Extract category (Men Elite, Women Elite) from race title."""
    if not title:
        return "Elite"
    title_lower = title.lower()
    if "women" in title_lower or "female" in title_lower:
        return "Women Elite"
    elif "men" in title_lower or "male" in title_lower:
        return "Men Elite"
    elif "u23" in title_lower:
        return "U23"
    elif "junior" in title_lower:
        return "Juniors"
    return "Elite"


def main():
    print("=" * 50)
    print("Cyclocross Race Ratings Scraper")
    print("=" * 50)
    
    # Load existing races
    existing_races = load_existing_races()
    existing_ids = {r.get("id") for r in existing_races}
    print(f"Loaded {len(existing_races)} existing races")
    
    # Fetch events
    events = get_race_events()
    
    # Filter for target series and past races
    today = datetime.now().date()
    filtered_events = []
    
    for event in events:
        series = event.get("series", "")
        event_date_str = event.get("date", "")
        
        # Check if it's a series we care about
        if not matches_target_series(series):
            continue
        
        # Parse date and check if it's in the past
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            if event_date > today:
                continue
        except:
            continue
        
        filtered_events.append(event)
    
    print(f"Found {len(filtered_events)} relevant past events")
    
    # Process each event
    new_races = []
    
    for event in filtered_events:
        event_id = event.get("event_id")
        
        # Skip if we already have this race
        if event_id in existing_ids:
            print(f"Skipping {event_id} - already processed")
            continue
        
        print(f"\nProcessing: {event.get('name')} ({event_id})")
        
        # Fetch results
        data = get_race_results(event_id)
        
        if not data:
            print("  No results found")
            continue
        
        # Get results from categories
        categories = data.get("categories", [])
        if not categories:
            print("  No categories found")
            continue
        
        results = categories[0].get("results", [])
        if not results:
            print("  No results in category")
            continue
        
        # Calculate rating
        score, stars = calculate_rating(results)
        
        # Extract category from title
        title = data.get("title", event.get("name", ""))
        category = extract_category_from_title(title)
        
        print(f"  Category: {category}")
        print(f"  Results: {len(results)} riders")
        print(f"  Score: {score}, Stars: {'⭐' * stars}")
        
        # Create race entry
        race = {
            "id": event_id,
            "name": event.get("name", "Unknown"),
            "date": event.get("date", ""),
            "series": event.get("series", ""),
            "location": event.get("location", event.get("country", "")),
            "category": category,
            "rating": stars,
            "score": score,
            "url": event.get("results_url", f"https://cyclocross24.com/race/{event_id}/")
        }
        
        new_races.append(race)
        existing_ids.add(event_id)
    
    # Combine with existing races
    all_races = existing_races + new_races
    
    # Sort by date (newest first)
    all_races.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # Save
    save_races(all_races)
    
    print(f"\n{'=' * 50}")
    print(f"Done! Added {len(new_races)} new races.")
    print(f"Total races: {len(all_races)}")


if __name__ == "__main__":
    main()
