const { proxyToBackend, withHandler } = require("./_backend");

async function download(req, res) {
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ detail: "Use POST /api/download" });
    return;
  }
  await proxyToBackend(req, res, "/api/download", { json: false });
}

const handler = withHandler(download);
handler.config = { maxDuration: 300 };
module.exports = handler;
