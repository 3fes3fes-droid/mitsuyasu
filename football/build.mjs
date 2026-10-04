import { build } from "esbuild";
import { readFile, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const root = fileURLToPath(new URL(".", import.meta.url));
await build({
  absWorkingDir: root,
  entryPoints: ["entry.tsx"],
  outfile: "app.js",
  bundle: true,
  minify: true,
  platform: "browser",
  format: "iife",
  jsx: "automatic",
  alias: { "@": root },
  nodePaths: process.env.FOOTBALL_NODE_MODULES ? [process.env.FOOTBALL_NODE_MODULES] : [],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  logLevel: "warning",
});
const source = await readFile(new URL("app.js", import.meta.url));
await writeFile(new URL("app.b64", import.meta.url), gzipSync(source, { level: 9 }).toString("base64") + "\n");
await rm(new URL("app.js", import.meta.url));
console.log(`Built GitHub football application: ${source.length} bytes before gzip`);
