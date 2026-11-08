/**
 * H8: layout checks on the built site, every page of every edition at phone (360 px),
 * tablet (768 px) and desktop (1280 px) widths.
 *
 * Fails when the page scrolls sideways, or when an element sticks out past the right
 * edge of the screen without being inside a container that scrolls (such as a wide
 * table in its scroll region). Layout does not depend on the colour scheme, so light
 * mode is enough here; a11y.mjs checks contrast in both.
 *
 *   npm run build && npm run layout
 */
import path from "node:path";

import { chromium } from "playwright";

import { listPages, serveSite } from "./lib/static-site.mjs";

const OUT = path.resolve(process.argv[2] ?? "out");
const WIDTHS = [360, 768, 1280];

const site = await serveSite(OUT);
const browser = await chromium.launch();
const urls = listPages(OUT);
let failures = 0;

for (const width of WIDTHS) {
  const context = await browser.newContext({
    viewport: { width, height: 800 },
  });
  const page = await context.newPage();
  for (const url of urls) {
    await page.goto(site.origin + url);
    const problems = await page.evaluate(() => {
      const found = [];
      const vw = document.documentElement.clientWidth;
      if (document.documentElement.scrollWidth > vw)
        found.push(
          `page is ${document.documentElement.scrollWidth} px wide, screen ${vw} px`,
        );
      // Inside a scroll container (overflow-x auto/scroll/hidden) is fine.
      const clipped = (el) => {
        for (let p = el.parentElement; p; p = p.parentElement) {
          const o = getComputedStyle(p).overflowX;
          if (o !== "visible") return true;
        }
        return false;
      };
      for (const el of document.body.querySelectorAll("*")) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.right > vw + 1 && !clipped(el)) {
          const name =
            el.tagName.toLowerCase() +
            (el.id ? `#${el.id}` : "") +
            (el.className && typeof el.className === "string"
              ? `.${el.className.split(" ")[0]}`
              : "");
          found.push(`${name} ends at ${Math.round(r.right)} px`);
          if (found.length > 5) break;
        }
      }
      return found;
    });
    for (const p of problems) {
      failures += 1;
      console.error(`${url} @ ${width} px: ${p}`);
    }
  }
  await context.close();
}

await browser.close();
site.close();
console.log(
  `layout: ${urls.length} pages × ${WIDTHS.length} widths, ${failures} problem${failures === 1 ? "" : "s"}`,
);
process.exit(failures ? 1 : 0);
