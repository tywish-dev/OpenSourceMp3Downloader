const form = document.getElementById("extract-form");
const urlInput = document.getElementById("url");
const inspectBtn = document.getElementById("inspect-btn");
const downloadBtn = document.getElementById("download-btn");
const statusEl = document.getElementById("status");
const card = document.getElementById("card");
const titleEl = document.getElementById("title");
const durationEl = document.getElementById("duration");
const extractorEl = document.getElementById("extractor-name");
const thumbEl = document.getElementById("thumb");
const healthLink = document.getElementById("health-link");

let inspectedUrl = "";

function apiBase() {
  return String(window.OSMP3_API_BASE || "").replace(/\/$/, "");
}

function apiUrl(path) {
  return `${apiBase()}${path}`;
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
  return `Request failed (${response.status})`;
}

if (healthLink) {
  healthLink.href = apiUrl("/health");
}

if (!apiBase() && /vercel\.app$/i.test(window.location.hostname)) {
  setStatus(
    "This Vercel site has no API URL yet. Set OSMP3_API_BASE to your Koyeb (or other) backend URL.",
    true,
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
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
        ? `${message} If the API just woke up, wait a few seconds and try again.`
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
