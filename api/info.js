const { proxyJson } = require("../lib/osmp3-backend");

module.exports = async function handler(req, res) {
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ detail: "Use POST /api/info" });
    return;
  }
  await proxyJson(req, res, "/api/info");
};
