const form = document.getElementById("scrape-form");
const urlInput = document.getElementById("url");
const keywordsInput = document.getElementById("keywords");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const pageTitleEl = document.getElementById("page-title");
const pageUrlEl = document.getElementById("page-url");
const wordCountEl = document.getElementById("word-count");
const totalMatchesEl = document.getElementById("total-matches");
const keywordListEl = document.getElementById("keyword-list");

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function highlight(snippet, keyword) {
  const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`(${escapedKeyword})`, "gi");
  return escapeHtml(snippet).replace(re, "<mark>$1</mark>");
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

function renderResults(data) {
  pageTitleEl.textContent = data.title || "(no page title)";
  pageUrlEl.textContent = data.url;
  pageUrlEl.href = data.url;
  wordCountEl.textContent = data.word_count.toLocaleString();
  totalMatchesEl.textContent = data.total_matches.toLocaleString();

  keywordListEl.innerHTML = "";
  for (const item of data.results) {
    const li = document.createElement("li");
    li.className = "keyword";
    const pillClass = item.count === 0 ? "count-pill zero" : "count-pill";
    const snippetsHtml = item.snippets.length
      ? `<ul class="snippets">${item.snippets
          .map((s) => `<li>${highlight(s, item.keyword)}</li>`)
          .join("")}</ul>`
      : `<p class="no-hits">No occurrences found.</p>`;
    li.innerHTML = `
      <div class="keyword-head">
        <span class="keyword-name">${escapeHtml(item.keyword)}</span>
        <span class="${pillClass}">${item.count} match${item.count === 1 ? "" : "es"}</span>
      </div>
      ${snippetsHtml}
    `;
    keywordListEl.appendChild(li);
  }
  resultsEl.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  const keywords = keywordsInput.value.trim();
  if (!url || !keywords) return;

  resultsEl.classList.add("hidden");
  setStatus("Fetching and scanning the page…", "loading");
  submitBtn.disabled = true;

  try {
    const response = await fetch("/api/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, keywords }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || `Request failed (${response.status})`, "error");
      return;
    }
    clearStatus();
    renderResults(data);
  } catch (err) {
    setStatus(`Network error: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
});
