import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = dirname(fileURLToPath(import.meta.url));
const base = (process.env.OSMP3_API_BASE || "").trim().replace(/\/$/, "");
writeFileSync(
  join(dir, "config.js"),
  `window.OSMP3_API_BASE = ${JSON.stringify(base)};\n`,
);
console.log(`Wrote web/config.js with OSMP3_API_BASE=${base || "(same origin)"}`);
