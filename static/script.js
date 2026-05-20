const form = document.getElementById("search-form");
const keywordsInput = document.getElementById("keywords");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const resultsHeadingEl = document.getElementById("results-heading");
const resultListEl = document.getElementById("result-list");

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

function renderResults(data) {
  const noun = data.count === 1 ? "result" : "results";
  resultsHeadingEl.textContent = `${data.count} ${noun} for "${data.query}"`;
  resultListEl.innerHTML = "";
  if (!data.results.length) {
    const li = document.createElement("li");
    li.className = "no-hits";
    li.textContent = "No pages matched.";
    resultListEl.appendChild(li);
  }
  for (const r of data.results) {
    const li = document.createElement("li");
    li.className = "result";
    const safeUrl = escapeHtml(r.url);
    li.innerHTML = `
      <a class="result-title" href="${safeUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.title)}</a>
      <a class="result-url" href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>
      <p class="result-snippet">${highlight(r.snippet, data.keywords)}</p>
    `;
    resultListEl.appendChild(li);
  }
  resultsEl.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const keywords = keywordsInput.value.trim();
  if (!keywords) return;

  resultsEl.classList.add("hidden");
  setStatus("Searching…", "loading");
  submitBtn.disabled = true;

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords }),
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
