const { backendBase, missingBackendResponse } = require("../lib/osmp3-backend");

module.exports = async function handler(req, res) {
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ detail: "Use POST /api/download" });
    return;
  }

  const base = backendBase();
  if (!base) {
    missingBackendResponse(res);
    return;
  }

  const response = await fetch(`${base}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req.body ?? {}),
  });

  if (!response.ok) {
    const text = await response.text();
    res.status(response.status);
    res.setHeader("Content-Type", response.headers.get("content-type") || "application/json");
    res.send(text);
    return;
  }

  const disposition = response.headers.get("content-disposition");
  if (disposition) {
    res.setHeader("Content-Disposition", disposition);
  }
  res.setHeader("Content-Type", response.headers.get("content-type") || "audio/mpeg");
  res.status(200);
  const buffer = Buffer.from(await response.arrayBuffer());
  res.send(buffer);
};

module.exports.config = { maxDuration: 300 };
