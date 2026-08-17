function backendBase() {
  return String(process.env.OSMP3_API_BASE || "")
    .trim()
    .replace(/\/+$/, "");
}

function requestJson(req) {
  if (req.body == null || req.body === "") {
    return {};
  }
  if (typeof req.body === "string") {
    try {
      return JSON.parse(req.body);
    } catch {
      return {};
    }
  }
  return req.body;
}

function missingBackend(res) {
  res.status(503).json({
    detail:
      "Set OSMP3_API_BASE in Vercel Production to your Northflank public URL (https://….code.run, no trailing slash), then Redeploy.",
  });
}

async function proxyToBackend(req, res, path, { json = true } = {}) {
  const base = backendBase();
  if (!base) {
    missingBackend(res);
    return;
  }
  if (!/^https:\/\//i.test(base)) {
    res.status(500).json({
      detail: `OSMP3_API_BASE must be an https URL, got: ${base}`,
    });
    return;
  }

  const init = {
    method: req.method,
    headers: { Accept: json ? "application/json" : "*/*" },
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(requestJson(req));
  }

  let response;
  try {
    response = await fetch(`${base}${path}`, init);
  } catch (error) {
    res.status(502).json({
      detail: `Could not reach Northflank (${base}): ${error.message}`,
    });
    return;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const text = await response.text();
    let detail = text.slice(0, 500);
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed.detail === "string") {
        detail = parsed.detail;
      }
    } catch {
      /* keep text */
    }
    res.status(response.status).json({ detail });
    return;
  }

  if (json || contentType.includes("application/json")) {
    const text = await response.text();
    res.status(response.status);
    res.setHeader("Content-Type", contentType || "application/json");
    res.send(text);
    return;
  }

  const disposition = response.headers.get("content-disposition");
  if (disposition) {
    res.setHeader("Content-Disposition", disposition);
  }
  res.setHeader("Content-Type", contentType || "audio/mpeg");
  res.status(200);
  res.send(Buffer.from(await response.arrayBuffer()));
}

function withHandler(fn) {
  return async function handler(req, res) {
    try {
      await fn(req, res);
    } catch (error) {
      console.error(error);
      if (!res.headersSent) {
        res.status(500).json({
          detail: error.message || "Vercel proxy crashed.",
        });
      }
    }
  };
}

module.exports = {
  backendBase,
  proxyToBackend,
  withHandler,
};
