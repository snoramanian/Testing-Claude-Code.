# Keyword Finder

A small Flask web app: type a few keywords, and the server queries
DuckDuckGo's public search and returns the pages that talk about those
keywords — titles, URLs, and snippets with the keywords highlighted.

## Features

- Single-input UI: just type keywords (comma-separated or freeform)
- Server-side search against DuckDuckGo's HTML endpoint (no API key)
- Top 10 results with title, URL, and highlighted snippet
- Case-insensitive keyword highlighting in snippets
- Vercel-ready (`api/index.py` + `vercel.json`)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000.

## Use

1. Type your keywords (e.g. `python web scraping` or `machine learning, python`).
2. Click **Find pages**.

You'll see up to 10 matching pages with the keywords highlighted in each snippet.

## API

`POST /api/search`

```json
{ "keywords": "python web scraping" }
```

Response:

```json
{
  "query": "python web scraping",
  "keywords": ["python", "web scraping"],
  "count": 2,
  "results": [
    {
      "url": "https://example.com/article",
      "title": "Intro to web scraping with Python",
      "snippet": "Learn how to scrape data using Python and BeautifulSoup..."
    }
  ]
}
```

## Notes

- Results come from DuckDuckGo's public HTML search. If you hit rate
  limits in production, swap in a real search API (Google Custom Search,
  Bing, SerpAPI).
- Be a polite user — don't hammer the search endpoint in a loop.
