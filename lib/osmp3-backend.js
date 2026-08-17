function backendBase() {
  return String(process.env.OSMP3_API_BASE || "")
    .trim()
    .replace(/\/+$/, "");
}

function missingBackendResponse(res) {
  res.status(503).json({
    detail:
      "Set OSMP3_API_BASE in Vercel (Production) to your Northflank public URL, e.g. https://http--osmp3--project--user.code.run — no trailing slash — then Redeploy.",
  });
}

async function proxyJson(req, res, path) {
  const base = backendBase();
  if (!base) {
    missingBackendResponse(res);
    return;
  }

  const response = await fetch(`${base}${path}`, {
    method: req.method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: req.method === "GET" || req.method === "HEAD" ? undefined : JSON.stringify(req.body ?? {}),
  });

  const text = await response.text();
  res.status(response.status);
  const contentType = response.headers.get("content-type") || "application/json";
  res.setHeader("Content-Type", contentType);
  res.send(text);
}

module.exports = { backendBase, missingBackendResponse, proxyJson };
