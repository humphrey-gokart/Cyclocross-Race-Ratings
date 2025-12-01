# CX Race Ratings

Spoiler-free cyclocross race ratings for catching up on races you missed.

**No results. No winners. Just ratings.**

## Live Site

`https://YOUR_USERNAME.github.io/cx-ratings/`

## How It Works

Ratings are automatically scraped and calculated based on **time gaps**:

| Rating | Meaning |
|--------|---------|
| ★★★★★ | Must watch - sprint finish |
| ★★★★☆ | Great race - very close |
| ★★★☆☆ | Good race |
| ★★☆☆☆ | Okay |
| ★☆☆☆☆ | Skip it - dominant win |

New races are discovered automatically from cyclocross24.com every day.

## Setup

1. **Create repo** on GitHub, upload all files
2. **Settings → Pages** → Deploy from `main` branch
3. **Settings → Actions → General** → Enable "Read and write permissions"
4. **Actions tab** → Run workflow manually

That's it! The scraper runs daily at 22:00 UTC.

## License

MIT
