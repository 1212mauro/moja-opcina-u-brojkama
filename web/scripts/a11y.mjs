/**
 * E4: axe-core accessibility checks on the built site (WCAG 2.1 A and AA rules).
 *
 * Serves `out/` (built without a base path), opens every page of every edition
 * in Chromium in light and dark mode, and fails if axe finds any violation.
 *
 *   npm run build && npm run a11y
 */
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

import { listPages, serveSite } from "./lib/static-site.mjs";

const OUT = path.resolve(process.argv[2] ?? "out");
const site = await serveSite(OUT);
const origin = site.origin;
const browser = await chromium.launch();
const urls = [...listPages(OUT), "/this-page-does-not-exist/"];
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
site.close();
console.log(
  `a11y: ${urls.length} pages × 2 colour schemes, ${failures} violation${failures === 1 ? "" : "s"}`,
);
process.exit(failures ? 1 : 0);
