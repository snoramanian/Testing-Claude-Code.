const form = document.getElementById("search-form");
const keywordsInput = document.getElementById("keywords");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const resultsHeadingEl = document.getElementById("results-heading");
const resultsMetaEl = document.getElementById("results-meta");
const resultListEl = document.getElementById("result-list");
const paginationEl = document.getElementById("pagination");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const pageLabelEl = document.getElementById("page-label");

let currentKeywords = "";
let currentPage = 1;
let currentHasMore = false;

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function highlight(text, keywords) {
  let escaped = escapeHtml(text);
  for (const kw of keywords) {
    if (!kw) continue;
    const escKw = kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(${escKw})`, "gi");
    escaped = escaped.replace(re, "<mark>$1</mark>");
  }
  return escaped;
}

function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = `status ${kind || ""}`.trim();
  statusEl.classList.remove("hidden");
}

function clearStatus() {
  statusEl.textContent = "";
  statusEl.className = "status hidden";
}

function renderPagination(page, hasMore) {
  pageLabelEl.textContent = `Page ${page}`;
  prevBtn.disabled = page <= 1;
  nextBtn.disabled = !hasMore;
  paginationEl.classList.remove("hidden");
}

function renderResults(data) {
  const startRank = (data.page - 1) * 50 + 1;
  const endRank = startRank + data.count - 1;
  const noun = data.count === 1 ? "result" : "results";
  resultsHeadingEl.textContent =
    `Page ${data.page} · ${data.count} ${noun} (#${startRank}–#${endRank}) for "${data.query}"`;
  resultsMetaEl.textContent =
    `Across ${data.unique_domains} unique domain${data.unique_domains === 1 ? "" : "s"} · ` +
    `${data.pages_fetched} search page${data.pages_fetched === 1 ? "" : "s"} fetched in parallel`;

  resultListEl.innerHTML = "";
  if (!data.results.length) {
    const li = document.createElement("li");
    li.className = "no-hits";
    li.textContent = data.page > 1 ? "No more results on this page." : "No pages matched.";
    resultListEl.appendChild(li);
  } else {
    for (const r of data.results) {
      const li = document.createElement("li");
      li.className = "result";
      const safeUrl = escapeHtml(r.url);
      const safeFavicon = escapeHtml(r.favicon || "");
      li.innerHTML = `
        <div class="result-meta">
          <span class="result-rank">#${r.rank}</span>
          ${safeFavicon ? `<img class="result-favicon" src="${safeFavicon}" alt="" loading="lazy" onerror="this.style.display='none'" />` : ""}
          <span class="result-domain">${escapeHtml(r.domain)}</span>
        </div>
        <a class="result-title" href="${safeUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.title)}</a>
        <a class="result-url" href="${safeUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.display_url || r.url)}</a>
        <p class="result-snippet">${highlight(r.snippet, data.keywords)}</p>
        <div class="result-footer">
          <span class="badge-soft">${r.snippet_length} chars</span>
        </div>
      `;
      resultListEl.appendChild(li);
    }
  }
  renderPagination(data.page, data.has_more);
  resultsEl.classList.remove("hidden");
}

async function runSearch(keywords, page) {
  resultsEl.classList.add("hidden");
  setStatus(`Searching page ${page}… (fetching multiple result pages in parallel)`, "loading");
  submitBtn.disabled = true;
  prevBtn.disabled = true;
  nextBtn.disabled = true;

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords, page }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || `Request failed (${response.status})`, "error");
      return;
    }
    clearStatus();
    currentKeywords = keywords;
    currentPage = data.page;
    currentHasMore = data.has_more;
    renderResults(data);
    window.scrollTo({ top: resultsEl.offsetTop - 20, behavior: "smooth" });
  } catch (err) {
    setStatus(`Network error: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const keywords = keywordsInput.value.trim();
  if (!keywords) return;
  runSearch(keywords, 1);
});

prevBtn.addEventListener("click", () => {
  if (currentPage > 1 && currentKeywords) {
    runSearch(currentKeywords, currentPage - 1);
  }
});

nextBtn.addEventListener("click", () => {
  if (currentHasMore && currentKeywords) {
    runSearch(currentKeywords, currentPage + 1);
  }
});
