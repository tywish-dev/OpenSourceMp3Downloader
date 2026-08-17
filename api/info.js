const { proxyToBackend, withHandler } = require("./_backend");

module.exports = withHandler(async function info(req, res) {
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ detail: "Use POST /api/info" });
    return;
  }
  await proxyToBackend(req, res, "/api/info");
});
