"""Flask keyword-driven web search with pagination.

Takes a list of keywords and returns the top web pages that contain
those keywords, sourced from DuckDuckGo's public HTML search endpoint.
Returns 50 results per page; supports requesting page 2, 3, ... up to
MAX_PAGE to surface more results. Each result is enriched with rank,
domain, display URL, favicon, and snippet length.
"""
import concurrent.futures
import re
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

REQUEST_TIMEOUT = 10
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
SEARCH_URL = "https://html.duckduckgo.com/html/"
RESULTS_PER_PAGE = 50
DDG_PAGE_SIZE = 30
MAX_PAGE = 4                          # cap page param to prevent abuse
MAX_DDG_FETCHES_PER_REQUEST = 8       # at most 8 upstream fetches per UI page
DEDUP_BUFFER = 30                     # extra raw rows beyond N*50 to survive dedup
MAX_PARALLEL_FETCHES = 5              # cap thread-pool size


def parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,\n]", raw):
        cleaned = part.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def unwrap_ddg_url(href: str) -> str:
    """DDG wraps result URLs as /l/?uddg=<urlencoded>. Unwrap them."""
    if not href:
        return href
    if href.startswith("//"):
        href = "https:" + href
    try:
        parsed = urlparse(href)
    except ValueError:
        return href
    if "uddg" in parsed.query:
        qs = parse_qs(parsed.query)
        candidates = qs.get("uddg", [])
        if candidates:
            return unquote(candidates[0])
    return href


def parse_ddg_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if not link:
            continue
        url = unwrap_ddg_url(link.get("href", ""))
        title = link.get_text(strip=True)
        if not url or not title:
            continue
        out.append({
            "url": url,
            "title": title,
            "snippet": snippet.get_text(" ", strip=True) if snippet else "",
        })
    return out


def fetch_one_page(query: str, offset: int) -> list[dict]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }
    data = {"q": query}
    if offset > 0:
        data["s"] = str(offset)
    resp = requests.post(
        SEARCH_URL,
        data=data,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return parse_ddg_results(resp.text)


def offsets_for_page(page: int) -> list[int]:
    """Return DDG offsets needed to surface UI page N.

    UI page N wants global ranks (N-1)*50+1 .. N*50, which after dedup we slice
    from the merged result list. We fetch enough DDG pages (each ~30 results)
    to cover that rank range plus a buffer for dedup loss, capped at
    MAX_DDG_FETCHES_PER_REQUEST.
    """
    needed_raw = page * RESULTS_PER_PAGE + DEDUP_BUFFER
    count = (needed_raw + DDG_PAGE_SIZE - 1) // DDG_PAGE_SIZE
    count = min(count, MAX_DDG_FETCHES_PER_REQUEST)
    return [i * DDG_PAGE_SIZE for i in range(count)]


def search_duckduckgo(query: str, page: int) -> tuple[list[dict], int, bool]:
    """Fetch upstream pages, dedupe, return (slice_for_page, fetches_used, has_more)."""
    offsets = offsets_for_page(page)
    fetches_used = len(offsets)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(offsets), MAX_PARALLEL_FETCHES)
    ) as ex:
        pages = list(ex.map(lambda off: fetch_one_page(query, off), offsets))

    seen: set[str] = set()
    merged: list[dict] = []
    for p in pages:
        for r in p:
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            merged.append(r)

    start = (page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    page_slice = merged[start:end]
    # has_more if we filled this page AND there are unrendered results beyond it,
    # AND we're not already at MAX_PAGE.
    has_more = len(page_slice) >= RESULTS_PER_PAGE and len(merged) > end and page < MAX_PAGE
    return page_slice, fetches_used, has_more


def enrich_result(r: dict, rank: int) -> dict:
    parsed = urlparse(r["url"])
    domain = parsed.hostname or ""
    if domain.startswith("www."):
        domain = domain[4:]
    path = parsed.path or ""
    display_url = domain + (path if path and path != "/" else "")
    snippet = r.get("snippet", "")
    return {
        "rank": rank,
        "url": r["url"],
        "title": r["title"],
        "snippet": snippet,
        "domain": domain,
        "display_url": display_url,
        "favicon": f"https://icons.duckduckgo.com/ip3/{domain}.ico" if domain else "",
        "snippet_length": len(snippet),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(silent=True) or {}
    keywords = parse_keywords(data.get("keywords") or "")

    if not keywords:
        return jsonify({"error": "Please provide at least one keyword."}), 400

    try:
        page = int(data.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(page, MAX_PAGE))

    query = " ".join(keywords)
    try:
        raw_results, fetches_used, has_more = search_duckduckgo(query, page)
    except requests.exceptions.Timeout:
        return jsonify({"error": "The search timed out."}), 504
    except requests.exceptions.SSLError:
        return jsonify({"error": "SSL error contacting the search engine."}), 502
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Could not reach the search engine."}), 502
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        return jsonify({"error": f"Search engine returned HTTP {status}."}), 502
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Search failed: {exc}"}), 502

    rank_offset = (page - 1) * RESULTS_PER_PAGE
    enriched = [enrich_result(r, rank_offset + i + 1) for i, r in enumerate(raw_results)]
    domains = sorted({r["domain"] for r in enriched if r["domain"]})

    return jsonify({
        "query": query,
        "keywords": keywords,
        "page": page,
        "max_page": MAX_PAGE,
        "has_more": has_more,
        "count": len(enriched),
        "pages_fetched": fetches_used,
        "unique_domains": len(domains),
        "results": enriched,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
