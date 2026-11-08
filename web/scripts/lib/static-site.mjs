/**
 * Serves the static export (`out/`, built without a base path) on a free local port,
 * and lists its pages. Shared by the a11y, layout and screenshot scripts.
 */
import { createReadStream, existsSync, readdirSync, statSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".geojson": "application/geo+json",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

/** Every page of the export: each index.html, as a URL path ending in "/". */
export function listPages(root, dir = root, prefix = "/") {
  const found = [];
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (name === "_next" || name === "data" || name.startsWith("__next"))
      continue;
    if (statSync(full).isDirectory())
      found.push(...listPages(root, full, `${prefix}${name}/`));
    else if (name === "index.html") found.push(prefix);
  }
  return found;
}

/** Starts the server; resolves to { origin, close }. Unknown paths get 404.html. */
export function serveSite(root) {
  const server = createServer((req, res) => {
    const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
    let file = path.join(root, url);
    if (url.endsWith("/")) file = path.join(file, "index.html");
    if (!file.startsWith(root) || !existsSync(file)) {
      res.writeHead(404, { "content-type": TYPES[".html"] });
      createReadStream(path.join(root, "404.html")).pipe(res);
      return;
    }
    res.writeHead(200, {
      "content-type": TYPES[path.extname(file)] ?? "application/octet-stream",
    });
    createReadStream(file).pipe(res);
  });
  return new Promise((resolve) =>
    server.listen(0, "127.0.0.1", () =>
      resolve({
        origin: `http://127.0.0.1:${server.address().port}`,
        close: () => server.close(),
      }),
    ),
  );
}
