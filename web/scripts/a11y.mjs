/**
 * E4: axe-core accessibility checks on the built site (WCAG 2.1 A and AA rules).
 *
 * Serves `out/` (built without a base path), opens every page of every edition
 * in Chromium in light and dark mode, and fails if axe finds any violation.
 *
 *   npm run build && npm run a11y
 */
import { createReadStream, existsSync, readdirSync, statSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

const OUT = path.resolve(process.argv[2] ?? "out");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

/** Every page of the export: each index.html, plus the 404 page. */
function pages(dir = OUT, prefix = "/") {
  const found = [];
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (name === "_next" || name === "data" || name.startsWith("__next"))
      continue;
    if (statSync(full).isDirectory())
      found.push(...pages(full, `${prefix}${name}/`));
    else if (name === "index.html") found.push(prefix);
  }
  return found;
}

function serve() {
  const server = createServer((req, res) => {
    const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
    let file = path.join(OUT, url);
    if (url.endsWith("/")) file = path.join(file, "index.html");
    if (!file.startsWith(OUT) || !existsSync(file)) {
      res.writeHead(404, { "content-type": TYPES[".html"] });
      createReadStream(path.join(OUT, "404.html")).pipe(res);
      return;
    }
    res.writeHead(200, {
      "content-type": TYPES[path.extname(file)] ?? "application/octet-stream",
    });
    createReadStream(file).pipe(res);
  });
  return new Promise((resolve) =>
    server.listen(0, "127.0.0.1", () => resolve(server)),
  );
}

const server = await serve();
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const urls = [...pages(), "/this-page-does-not-exist/"];
let failures = 0;

for (const colorScheme of ["light", "dark"]) {
  const context = await browser.newContext({ colorScheme });
  const page = await context.newPage();
  for (const url of urls) {
    await page.goto(origin + url);
    // The search box exists only after hydration: wait for it, so axe checks it too.
    if (await page.$("[data-search-list]"))
      await page.waitForSelector('input[type="search"]');
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    for (const v of violations) {
      failures += 1;
      console.error(
        `\n${url} (${colorScheme}): ${v.id} [${v.impact}] ${v.help}`,
      );
      for (const node of v.nodes.slice(0, 5))
        console.error(
          `  ${node.target.join(" ")}\n    ${node.failureSummary.replace(/\n/g, "\n    ")}`,
        );
    }
  }
  await context.close();
}

await browser.close();
server.close();
console.log(
  `a11y: ${urls.length} pages × 2 colour schemes, ${failures} violation${failures === 1 ? "" : "s"}`,
);
process.exit(failures ? 1 : 0);
