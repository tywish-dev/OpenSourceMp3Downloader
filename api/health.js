const { proxyToBackend, withHandler } = require("./_backend");

module.exports = withHandler(async function health(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.status(405).json({ detail: "Use GET /health" });
    return;
  }
  await proxyToBackend(req, res, "/health");
});
