const form = document.getElementById("extract-form");
const urlInput = document.getElementById("url");
const apiBaseInput = document.getElementById("api-base");
const saveApiBtn = document.getElementById("save-api");
const inspectBtn = document.getElementById("inspect-btn");
const downloadBtn = document.getElementById("download-btn");
const statusEl = document.getElementById("status");
const card = document.getElementById("card");
const titleEl = document.getElementById("title");
const durationEl = document.getElementById("duration");
const extractorEl = document.getElementById("extractor-name");
const thumbEl = document.getElementById("thumb");
const healthLink = document.getElementById("health-link");
const apiTarget = document.getElementById("api-target");

const API_STORAGE_KEY = "osmp3-api-base";
let inspectedUrl = "";

function normalizeApiBase(value) {
  return String(value || "")
    .trim()
    .replace(/\/+$/, "");
}

function storedApiBase() {
  try {
    return normalizeApiBase(localStorage.getItem(API_STORAGE_KEY));
  } catch {
    return "";
  }
}

function apiBase() {
  return storedApiBase() || normalizeApiBase(window.OSMP3_API_BASE);
}

function apiUrl(path) {
  return `${apiBase()}${path}`;
}

function needsRemoteApi() {
  return /\.(vercel\.app|vercel\.sh)$/i.test(window.location.hostname);
}

function refreshApiChrome() {
  if (healthLink) {
    healthLink.href = apiUrl("/health");
  }
  if (apiTarget) {
    const base = apiBase();
    apiTarget.textContent = base ? `API ${base}` : "API (same origin)";
  }
}

function describeHttpError(response, fallback) {
  if (response.status === 404) {
    return "Vercel /api 404: wait for the latest deploy, or paste the Northflank https://…code.run URL above and Save.";
  }
  if (response.status === 503) {
    return fallback;
  }
  return fallback;
}

function selectedBitrate() {
  const picked = document.querySelector('input[name="bitrate"]:checked');
  return Number(picked ? picked.value : 192);
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function setBusy(busy) {
  document.body.classList.toggle("busy", busy);
  inspectBtn.disabled = busy;
  downloadBtn.disabled = busy || !inspectedUrl;
}

function filenameFromDisposition(header, fallback) {
  if (!header) {
    return fallback;
  }
  const utf = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf) {
    return decodeURIComponent(utf[1]);
  }
  const plain = header.match(/filename="?([^"]+)"?/i);
  return plain ? plain[1] : fallback;
}

function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) {
    return "Duration unknown";
  }
  const total = Math.round(Number(seconds));
  const mins = Math.floor(total / 60);
  const secs = String(total % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

async function readError(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
      return payload.detail[0].msg;
    }
  } catch {
    /* fall through */
  }
  return describeHttpError(response, `Request failed (${response.status})`);
}

function saveApiBaseFromInput() {
  const value = normalizeApiBase(apiBaseInput.value);
  try {
    if (value) {
      localStorage.setItem(API_STORAGE_KEY, value);
    } else {
      localStorage.removeItem(API_STORAGE_KEY);
    }
  } catch {
    setStatus("Could not save the API URL in this browser.", true);
    return false;
  }
  refreshApiChrome();
  setStatus(value ? `API set to ${value}` : "API cleared; this Vercel site will proxy /api if OSMP3_API_BASE is set.");
  return true;
}

if (apiBaseInput) {
  apiBaseInput.value = apiBase();
}
refreshApiChrome();
if (saveApiBtn) {
  saveApiBtn.addEventListener("click", () => {
    saveApiBaseFromInput();
  });
}

if (needsRemoteApi() && !apiBase()) {
  setStatus(
    "Leave the API field empty to use Vercel /api (set OSMP3_API_BASE in Vercel), or paste your Northflank https://….code.run URL and Save.",
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (apiBaseInput && apiBaseInput.value.trim()) {
    saveApiBaseFromInput();
  }
  const url = urlInput.value.trim();
  inspectedUrl = "";
  downloadBtn.disabled = true;
  card.hidden = true;
  setBusy(true);
  setStatus("Reading the source…");

  try {
    const response = await fetch(apiUrl("/api/info"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const info = await response.json();
    inspectedUrl = url;
    titleEl.textContent = info.title || "Untitled";
    extractorEl.textContent = info.extractor || "source";
    durationEl.textContent = formatDuration(info.duration);
    if (info.thumbnail) {
      thumbEl.src = info.thumbnail;
      thumbEl.hidden = false;
    } else {
      thumbEl.removeAttribute("src");
      thumbEl.hidden = true;
    }
    card.hidden = false;
    setStatus("Looks good. Download when you are ready.");
  } catch (error) {
    const message = error.message || "Could not inspect that URL.";
    const likelyCold =
      error.name === "TypeError" || /failed to fetch|networkerror/i.test(message);
    setStatus(
      likelyCold
        ? `${message} Check the API URL, that Northflank HTTP is public/active, and /health returns ok.`
        : message,
      true,
    );
  } finally {
    setBusy(false);
  }
});

downloadBtn.addEventListener("click", async () => {
  if (!inspectedUrl) {
    return;
  }
  setBusy(true);
  setStatus("Extracting audio. This can take a bit…");
  try {
    const response = await fetch(apiUrl("/api/download"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: inspectedUrl,
        bitrate: selectedBitrate(),
      }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const blob = await response.blob();
    const filename = filenameFromDisposition(
      response.headers.get("content-disposition"),
      "audio.mp3",
    );
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(href);
    setStatus(`Saved ${filename}`);
  } catch (error) {
    setStatus(error.message || "Download failed.", true);
  } finally {
    setBusy(false);
  }
});
