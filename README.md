# CX Race Ratings

Spoiler-free cyclocross race ratings for catching up on races you missed.

**No results. No winners. Just ratings.**

## Live Site

Visit: `https://YOUR_USERNAME.github.io/cx-ratings/`

## How It Works

Ratings are automatically scraped from race results and calculated based on **time gaps** - the closer the finish, the higher the rating. The algorithm considers:

- Gap between 1st and 2nd place (most important)
- Gap between 1st and 3rd place  
- Number of riders finishing within 10 seconds

| Rating | Meaning | Typical gaps |
|--------|---------|--------------|
| ★★★★★ | Must watch | Sprint finish or <3 seconds |
| ★★★★☆ | Great race | <10 second gap, close podium |
| ★★★☆☆ | Good race | <30 second gap |
| ★★☆☆☆ | Okay | 30-60 second gap |
| ★☆☆☆☆ | Skip it | Dominant solo win |

## Setup

### 1. Fork & Enable Pages

1. Fork this repo
2. Go to Settings → Pages → Deploy from `main` branch, `/` root

### 2. Set up ScraperAPI (free)

The scraper uses [ScraperAPI](https://www.scraperapi.com/) to reliably fetch data without getting blocked.

1. Sign up at https://www.scraperapi.com/ (free tier: 1,000 requests/month)
2. Copy your API key from the dashboard
3. In your repo: Settings → Secrets and variables → Actions → New repository secret
4. Name: `SCRAPER_API_KEY`, Value: your API key

### 3. Enable Actions

1. Settings → Actions → General
2. Enable "Read and write permissions" under Workflow permissions
3. Manually trigger first run: Actions → Update CX Ratings → Run workflow

## Automatic Updates

A GitHub Action runs daily at 22:00 UTC to:
1. Scrape latest results from cyclocross24.com via ScraperAPI  
2. Calculate excitement ratings from time gaps
3. Update `races.json` automatically

## Adding New Races

Edit `CYCLOCROSS24_RACES` in `scraper.py`:

```python
{"id": 17817, "series": "UCI World Cup", "venue": "Tábor", "country": "CZE", "date": "2025-11-23", "category": "Elite Men"},
```

To find race IDs:
1. Visit cyclocross24.com
2. Navigate to the race results page
3. Get the ID from the URL: `/race/17817/` → ID is `17817`

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (optional but recommended)
export SCRAPER_API_KEY=your_key_here

# Run scraper
python scraper.py

# Test the site
python -m http.server 8000
# Open http://localhost:8000
```

## Races Covered

- UCI World Cup (12 rounds)
- Superprestige (8 rounds)  
- X2O Trofee (8 rounds)
- European Championships
- World Championships

Both Elite Men and Elite Women categories.

## Manual Override

If you disagree with an auto-calculated rating, edit `races.json` directly. Manual entries won't be overwritten unless the date/venue/category match exactly.

## License

MIT - do what you want with it.
