"""Flask keyword-driven web search.

Takes a list of keywords and returns the top web pages that contain
those keywords, sourced from DuckDuckGo's public HTML search endpoint.
"""
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
MAX_RESULTS = 10


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
        if len(out) >= MAX_RESULTS:
            break
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


def search_duckduckgo(query: str) -> list[dict]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }
    resp = requests.post(
        SEARCH_URL,
        data={"q": query},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return parse_ddg_results(resp.text)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(silent=True) or {}
    keywords = parse_keywords(data.get("keywords") or "")

    if not keywords:
        return jsonify({"error": "Please provide at least one keyword."}), 400

    query = " ".join(keywords)
    try:
        results = search_duckduckgo(query)
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

    return jsonify({
        "query": query,
        "keywords": keywords,
        "count": len(results),
        "results": results,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
