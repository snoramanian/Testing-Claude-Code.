# Web Scraper & Keyword Finder

A small Flask web app: paste a URL, list a few keywords, and the server fetches
the page, strips boilerplate, and reports how many times each keyword appears —
with surrounding context snippets.

## Features

- Server-side scraping with `requests` + `BeautifulSoup` (no browser CORS issues)
- Case-insensitive keyword matching with highlighted context snippets
- URL normalization (adds `http://` if missing), HTTPS support, redirect following
- 5 MB page-size cap, 15 s timeout, content-type guard (HTML/XML only)
- Clean responsive UI

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000.

## Use

1. Enter a URL (e.g. `https://en.wikipedia.org/wiki/Web_scraping`).
2. Enter keywords separated by commas (e.g. `python, crawler, parser`).
3. Click **Scan page**.

You'll see total match counts, per-keyword counts, and up to 5 highlighted
context snippets per keyword.

## API

`POST /api/scrape`

```json
{ "url": "https://example.com", "keywords": "alpha, beta" }
```

Response:

```json
{
  "url": "https://example.com/",
  "title": "Example Domain",
  "word_count": 28,
  "total_matches": 1,
  "results": [
    { "keyword": "alpha", "count": 0, "snippets": [] },
    { "keyword": "beta",  "count": 1, "snippets": ["…in beta release…"] }
  ]
}
```

## Notes

Be a polite scraper — honor each site's robots.txt and terms of service. This
tool is meant for small, ad-hoc lookups, not bulk crawling.
