/**
 * H8/H9: full-page screenshots of the built site for visual QA and the submission.
 *
 * Serves `out/` itself and captures each page at 360, 768 and 1280 px, in light and
 * dark mode. Pages default to the home page, a municipality page, the methodology
 * and the sources page of all three editions.
 *
 *   npm run build && node scripts/screenshots.mjs <outDir> [--top] [paths...]
 *
 * --top captures only the first screen instead of the full page (the submission set
 * in docs/screenshots/). From Git Bash, set MSYS_NO_PATHCONV=1 so "/" stays a path.
 *
 * Files are named <path>--<width>-<scheme>.png, e.g. opcina_lepoglava--360-dark.png.
 */
import { mkdirSync } from "node:fs";
import path from "node:path";

import { chromium } from "playwright";

import { serveSite } from "./lib/static-site.mjs";

const args = process.argv.slice(2);
const top = args.includes("--top");
const [outDir = "screenshots", ...given] = args.filter((a) => a !== "--top");
const OUT = path.resolve("out");
const WIDTHS = [360, 768, 1280];
const SCHEMES = ["light", "dark"];
const PATHS = given.length
  ? given
  : [
      "/",
      "/opcina/lepoglava/",
      "/metodologija/",
      "/izvori/",
      "/jednostavno/",
      "/jednostavno/opcina/lepoglava/",
      "/en/",
      "/en/municipality/lepoglava/",
    ];

mkdirSync(outDir, { recursive: true });
const site = await serveSite(OUT);
const browser = await chromium.launch();

for (const width of WIDTHS) {
  for (const colorScheme of SCHEMES) {
    const context = await browser.newContext({
      viewport: { width, height: 800 },
      colorScheme,
    });
    const page = await context.newPage();
    for (const p of PATHS) {
      await page.goto(site.origin + p, { waitUntil: "networkidle" });
      const name = p.replace(/^\/|\/$/g, "").replace(/\//g, "_") || "home";
      await page.screenshot({
        path: path.join(outDir, `${name}--${width}-${colorScheme}.png`),
        fullPage: !top,
      });
    }
    await context.close();
  }
}

await browser.close();
site.close();
console.log(
  `screenshots: ${PATHS.length} pages × ${WIDTHS.length} widths × ${SCHEMES.length} schemes in ${outDir}`,
);
