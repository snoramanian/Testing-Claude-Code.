"""Flask web scraper and keyword finder."""
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

REQUEST_TIMEOUT = 15
MAX_CONTENT_BYTES = 5 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (compatible; KeywordFinderBot/1.0; "
    "+https://github.com/snoramanian/testing-claude-code.)"
)
SNIPPET_RADIUS = 60
MAX_SNIPPETS_PER_KEYWORD = 5


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "http://" + url
    return url


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


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


def fetch_page(url: str) -> tuple[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    with requests.get(
        url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True
    ) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "html" not in content_type.lower() and "xml" not in content_type.lower():
            raise ValueError(f"Unsupported content type: {content_type or 'unknown'}")
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_CONTENT_BYTES:
                raise ValueError("Page is too large to scan (limit 5 MB).")
            chunks.append(chunk)
        body = b"".join(chunks)
        encoding = resp.encoding or "utf-8"
        try:
            return body.decode(encoding, errors="replace"), str(resp.url)
        except LookupError:
            return body.decode("utf-8", errors="replace"), str(resp.url)


def extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return title, text


def find_keyword_hits(text: str, keyword: str) -> tuple[int, list[str]]:
    if not keyword:
        return 0, []
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    matches = list(pattern.finditer(text))
    snippets: list[str] = []
    for m in matches[:MAX_SNIPPETS_PER_KEYWORD]:
        start = max(0, m.start() - SNIPPET_RADIUS)
        end = min(len(text), m.end() + SNIPPET_RADIUS)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        snippets.append(prefix + text[start:end].strip() + suffix)
    return len(matches), snippets


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json(silent=True) or {}
    raw_url = (data.get("url") or "").strip()
    keywords = parse_keywords(data.get("keywords") or "")

    if not raw_url:
        return jsonify({"error": "Please provide a URL."}), 400
    if not keywords:
        return jsonify({"error": "Please provide at least one keyword."}), 400

    url = normalize_url(raw_url)
    if not is_valid_http_url(url):
        return jsonify({"error": "URL must be a valid http(s) address."}), 400

    try:
        html, final_url = fetch_page(url)
    except requests.exceptions.Timeout:
        return jsonify({"error": "The request timed out."}), 504
    except requests.exceptions.SSLError:
        return jsonify({"error": "SSL error while contacting the site."}), 502
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Could not connect to the site."}), 502
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        return jsonify({"error": f"Site returned HTTP {status}."}), 502
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Request failed: {exc}"}), 502

    title, text = extract_text(html)
    word_count = len(text.split())

    results = []
    total_matches = 0
    for kw in keywords:
        count, snippets = find_keyword_hits(text, kw)
        total_matches += count
        results.append({"keyword": kw, "count": count, "snippets": snippets})

    return jsonify({
        "url": final_url,
        "title": title,
        "word_count": word_count,
        "total_matches": total_matches,
        "results": results,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
