import { chromium } from "playwright";
const [, , outDir, base, ...paths] = process.argv;
const browser = await chromium.launch();
for (const [w, h, tag] of [[1280, 800, "desk"], [375, 812, "mob"]]) {
  for (const scheme of ["light", "dark"]) {
    if (tag === "mob" && scheme === "dark") continue;
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    for (const p of paths) {
      await page.goto(base + p, { waitUntil: "networkidle" });
      const name = (p.replace(/\//g, "_") || "home") + `-${tag}-${scheme}.png`;
      await page.screenshot({ path: `${outDir}/${name}`, fullPage: true });
    }
    await ctx.close();
  }
}
await browser.close();
