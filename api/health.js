const { proxyJson } = require("../lib/osmp3-backend");

module.exports = async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.status(405).json({ detail: "Use GET /health" });
    return;
  }
  await proxyJson(req, res, "/health");
};
