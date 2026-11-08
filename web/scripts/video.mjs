/**
 * G5: the video presentation, recorded from the built site.
 *
 * One resident's question, answered on the site, with Croatian captions on screen
 * and a visible cursor. Every scene has a caption (on screen) and a narration (read
 * aloud over the video by a person). The script also writes, with the real timings
 * of this recording:
 *   - <outDir>/predstavljanje.webm   the recording (convert to MP4 with ffmpeg)
 *   - <outDir>/predstavljanje.srt    the captions as subtitles
 *   - <outDir>/naracija.md           the narration with start times, to read aloud
 *
 *   npm run build && node scripts/video.mjs <outDir>
 */
import { mkdirSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";

import { chromium } from "playwright";

import { serveSite } from "./lib/static-site.mjs";

const outDir = path.resolve(process.argv[2] ?? "video");
const LIVE_URL = "https://1212mauro.github.io/moja-opcina-u-brojkama/";
// A 1920×1080 window with the page zoomed 1.5×: the 1280 px desktop layout, sharp at
// full HD (recordings do not use the device pixel ratio, so zoom does the scaling).
const VIDEO = { width: 1920, height: 1080 };
const ZOOM = 1.5;
// Brisk Croatian narration: about 2.8 words a second (a normal speaking pace).
const WORDS_PER_SECOND = 2.8;

mkdirSync(outDir, { recursive: true });
const site = await serveSite(path.resolve("out"));
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: VIDEO,
  colorScheme: "light",
  recordVideo: { dir: outDir, size: VIDEO },
});

// A cursor and a caption bar on every page (recordings show no system cursor), and the
// page zoom. Pages made with setContent get it from setPage(), as init scripts do not
// run for them.
const overlay = (zoom) => {
  // Only the top page: frames inside it (the phones) are scaled with their parent.
  if (window !== window.top) return;
  const install = () => {
    if (document.getElementById("video-cursor")) return;
    const style = document.createElement("style");
    style.textContent = `
      body { zoom: ${zoom}; }
      #video-cursor { position: fixed; z-index: 2147483647; width: 32px; height: 32px;
        margin: -16px 0 0 -16px; border-radius: 50%; pointer-events: none;
        background: rgba(42,120,214,.35); border: 2px solid #1c5cab;
        transition: transform .15s ease-out; left: -50px; top: -50px; }
      #video-cursor.down { transform: scale(.7); background: rgba(42,120,214,.6); }
      #video-caption { position: fixed; z-index: 2147483646; left: 50%; bottom: 28px;
        transform: translateX(-50%); max-width: 1500px; padding: 16px 36px;
        border-radius: 12px; background: rgba(11,11,11,.86); color: #fff;
        font: 600 38px/1.35 system-ui, "Segoe UI", sans-serif; text-align: center;
        opacity: 0; transition: opacity .25s ease-out; pointer-events: none; }
      #video-caption.on { opacity: 1; }`;
    document.head.append(style);
    const cursor = Object.assign(document.createElement("div"), {
      id: "video-cursor",
    });
    const caption = Object.assign(document.createElement("div"), {
      id: "video-caption",
    });
    // Outside <body>, so the zoom does not move or scale them.
    document.documentElement.append(cursor, caption);
    addEventListener("mousemove", (e) => {
      cursor.style.left = `${e.clientX}px`;
      cursor.style.top = `${e.clientY}px`;
    });
    addEventListener("mousedown", () => cursor.classList.add("down"));
    addEventListener("mouseup", () => cursor.classList.remove("down"));
  };
  if (document.body) install();
  else addEventListener("DOMContentLoaded", install);
};
await context.addInitScript(overlay, ZOOM);

const page = await context.newPage();
const t0 = Date.now();
const timeline = []; // { start, end, caption, narration }
let mouse = { x: VIDEO.width / 2, y: VIDEO.height / 2 };

const wait = (ms) => page.waitForTimeout(ms);
const now = () => (Date.now() - t0) / 1000;

async function caption(text) {
  await page.evaluate((t) => {
    const el = document.getElementById("video-caption");
    if (!el) return;
    el.textContent = t;
    el.classList.toggle("on", Boolean(t));
  }, text);
}

/**
 * One scene: caption on, actions, then hold until the narration has had time to be
 * read aloud (at least `hold` ms after the actions). Timings go to the timeline.
 */
async function scene(text, narration, actions, hold = 800, shows = "") {
  const start = now();
  await caption(text);
  await actions();
  const spoken = narration.split(/\s+/).length / WORDS_PER_SECOND + 0.3;
  await wait(Math.max(hold, (spoken - (now() - start)) * 1000));
  timeline.push({ start, end: now(), caption: text, narration, shows });
}

async function moveTo(locator) {
  const box = await locator.boundingBox();
  const x = box.x + Math.min(box.width / 2, 120);
  const y = box.y + box.height / 2;
  await page.mouse.move(mouse.x, mouse.y);
  await page.mouse.move(x, y, { steps: 12 });
  mouse = { x, y };
}

async function click(locator) {
  await locator.scrollIntoViewIfNeeded();
  await moveTo(locator);
  await wait(150);
  await page.mouse.down();
  await page.mouse.up();
}

/** Smooth scroll so a section's top sits just below the top of the screen. */
async function scrollToSelector(selector, offset = 24) {
  await page.evaluate(
    ([sel, off]) => {
      const el = document.querySelector(sel);
      const y = el.getBoundingClientRect().top + scrollY - off;
      scrollTo({ top: y, behavior: "smooth" });
    },
    [selector, offset],
  );
  await wait(900);
}

async function scrollBy(dy) {
  await page.evaluate((d) => scrollBy({ top: d, behavior: "smooth" }), dy);
  await wait(800);
}

/** A page of our own (title cards, the phones), sized in real pixels: no zoom. */
async function setPage(html) {
  await page.setContent(html);
  await page.evaluate(overlay, 1);
}

const CARD_STYLE = `margin:0;height:100vh;display:grid;place-content:center;gap:30px;
  background:#f6f5f2;color:#0b0b0b;font-family:system-ui,'Segoe UI',sans-serif;text-align:center`;

async function titleCard(heading, lines) {
  await setPage(`<!doctype html><html lang="hr"><meta charset="utf-8">
    <body style="${CARD_STYLE}">
      <h1 style="margin:0;font-size:84px">${heading}</h1>
      ${lines.map((l) => `<p style="margin:0;font-size:42px;color:#52514e">${l}</p>`).join("")}
    </body></html>`);
}

/** A card with a heading and free-form content (lists, the architecture diagram). */
async function infoCard(heading, body) {
  await setPage(`<!doctype html><html lang="hr"><meta charset="utf-8">
    <style>
      .grid { display:grid; grid-template-columns:repeat(2, 640px); gap:22px 40px;
        text-align:left; margin:0 auto; }
      .item { background:#fff; border:2px solid #dcdad3; border-radius:16px; padding:18px 26px; }
      .item b { display:block; font-size:34px; }
      .item span { font-size:28px; color:#52514e; }
      .flow { display:flex; align-items:center; gap:14px; justify-content:center; }
      .box { width:290px; min-height:170px; box-sizing:border-box; display:grid;
        align-content:center; gap:8px; background:#fff; border:3px solid #1c5cab;
        border-radius:18px; padding:16px; }
      .box b { font-size:32px; } .box span { font-size:24px; color:#52514e; }
      .arrow { font-size:56px; color:#1c5cab; }
      .note { margin:0; font-size:32px; color:#52514e; }
    </style>
    <body style="${CARD_STYLE};padding-bottom:140px;box-sizing:border-box">
      <h1 style="margin:0 0 10px;font-size:72px">${heading}</h1>
      ${body}
    </body></html>`);
}

const items = (list) =>
  `<div class="grid">${list
    .map(([b, s]) => `<div class="item"><b>${b}</b><span>${s}</span></div>`)
    .join("")}</div>`;

// --- The story ---------------------------------------------------------------------

await scene(
  "",
  "Koliko novca ima vaš grad ili općina i na što ga troši? Ti su podaci javni, ali razbacani po desetak službenih stranica i tablica koje je teško čitati.",
  async () => {
    await titleCard("Moja općina u brojkama", [
      "Koliko novca ima vaše mjesto i na što ga troši?",
      "Jedna stranica za svaki grad i općinu, iz javnih podataka.",
    ]);
  },
  2500,
  "Naslovna kartica: „Moja općina u brojkama”, s pitanjem koje aplikacija rješava.",
);

await scene(
  "Za koga je",
  "Moja općina u brojkama napravljena je za stanovnike koji žele znati kamo ide njihov novac, za vijećnike, novinare i udruge, i za same općine koje se žele usporediti sa sličnima.",
  async () => {
    await infoCard(
      "Za koga je?",
      items([
        ["Stanovnici", "kamo ide novac mog mjesta?"],
        ["Vijećnici", "brojke prije sjednice o proračunu"],
        ["Novinari i udruge", "nabava i isplate na jednom mjestu"],
        ["Gradovi i općine", "usporedba sa sličnim mjestima"],
      ]),
    );
  },
  2000,
  "Kartica „Za koga je?”: četiri skupine korisnika i što svaka dobiva.",
);

await page.goto(site.origin + "/");
await scene(
  "Upišite ime mjesta ili poštanski broj",
  "Na početnoj stranici upišete ime svog mjesta ili poštanski broj.",
  async () => {
    const input = page.locator('input[type="search"]');
    await click(input);
    await page.keyboard.type("Lepo", { delay: 110 });
  },
  800,
  "Početna stranica. Pokazivač klikne u tražilicu i upiše „Lepo”; popis se suzi na Lepoglavu.",
);

await scene(
  "Svaki grad i općina ima svoju stranicu",
  "Svaki od 28 gradova i općina Varaždinske županije ima svoju stranicu. Otvorimo Lepoglavu.",
  async () => {
    await click(page.getByRole("link", { name: "Lepoglava" }).first());
    await page.waitForLoadState("networkidle");
  },
  800,
  "Klik na Lepoglavu; otvara se stranica grada.",
);

await scene(
  "Najvažnije brojke odmah na vrhu",
  "Na vrhu su najvažnije brojke: koliko je grad prošle godine dobio i potrošio, i koliko je ugovora javne nabave sklopio.",
  async () => {
    await moveTo(page.locator("section[aria-label] >> nth=0"));
  },
  800,
  "Zaglavlje stranice: ime, karta županije s označenom Lepoglavom i tri ključne brojke.",
);

await scene(
  "Usporedba sa sličnim mjestima",
  "Uz svaku brojku je i usporedba: Lepoglava po stanovniku troši 21 posto manje od sličnih gradova.",
  async () => {
    await moveTo(page.getByRole("link", { name: /21 % manje/ }));
  },
  800,
  "Pokazivač na poveznici „21 % manje nego slična mjesta” ispod rashoda.",
);

await scene(
  "Odakle dolazi novac i na što se troši",
  "U dijelu o proračunu vidi se odakle novac dolazi i na što se troši, od obrazovanja do prometa.",
  async () => {
    await scrollToSelector("#proracun");
    await scrollBy(420);
  },
  1000,
  "Pomicanje do odjeljka o proračunu: grafikoni prihoda po vrsti i rashoda po namjeni.",
);

await scene(
  "Uz svaki grafikon i tablica s brojkama",
  "Uz svaki grafikon je i tablica s točnim iznosima, pa brojke može pročitati i čitač zaslona.",
  async () => {
    const more = page.locator("#proracun details summary").first();
    await click(more);
    await wait(600);
    await scrollBy(260);
  },
  1000,
  "Klik otvara tablicu s točnim iznosima ispod grafikona.",
);

await scene(
  "Usporedba s gradovima iste veličine",
  "Zatim slijedi usporedba s gradovima i općinama iste vrste i veličine u županiji.",
  async () => {
    await scrollToSelector("#usporedba");
  },
  800,
  "Odjeljak „Usporedba”: Lepoglava uz slične jedinice, po stanovniku.",
);

await scene(
  "Javna nabava: od koga grad kupuje",
  "Javna nabava pokazuje od koga grad najviše kupuje i koji su najnoviji ugovori.",
  async () => {
    await scrollToSelector("#javna-nabava");
    await scrollBy(380);
  },
  1000,
  "Odjeljak „Javna nabava”: najveći dobavljači i najnoviji ugovori.",
);

await scene(
  "Isplate iz proračuna: kome grad plaća",
  "Isplate pokazuju kome grad plaća, mjesec po mjesec. Imena privatnih osoba nikad se ne prikazuju.",
  async () => {
    await scrollToSelector("#isplate");
    await scrollBy(320);
  },
  1500,
  "Odjeljak „Isplate”: iznosi po mjesecima i najveći primatelji.",
);

await scene(
  "Škole, vrtići i zdravstvo u blizini",
  "Tu su i škole, vrtići i ambulante u gradu.",
  async () => {
    await scrollToSelector("#ustanove");
  },
  1000,
  "Odjeljak „Ustanove”: škole, vrtići i zdravstvene ustanove.",
);

await scene(
  "Svaki broj ima izvor i datum preuzimanja",
  "Svaki broj ima izvor i datum preuzimanja, a podaci se osvježavaju automatski svake noći.",
  async () => {
    await scrollToSelector("#izvori");
  },
  800,
  "Odjeljak „Izvori”: izdavač, poveznica, licenca i datum preuzimanja za svaki skup podataka.",
);

await scene(
  "16 skupova otvorenih podataka",
  "Podaci dolaze iz šesnaest skupova otvorenih podataka: Ministarstva financija, javne nabave, Zavoda za statistiku, Geodetske uprave, Portala otvorenih podataka i samih gradova. Povezujemo ih preko šifre općine i OIB-a.",
  async () => {
    await infoCard(
      "Izvori podataka",
      items([
        ["Ministarstvo financija", "proračuni 2019–2025, registar proračunskih korisnika"],
        ["EOJN RH i TED", "ugovori javne nabave"],
        ["Državni zavod za statistiku", "popis 2021. i procjene stanovništva"],
        ["Državna geodetska uprava", "granice gradova i općina"],
        ["data.gov.hr (MZOM)", "škole i dječji vrtići"],
        ["Gradovi i općine", "isplate iz proračuna, registri ugovora"],
      ]) +
        `<p class="note">Povezano preko šifre općine (DZS) i OIB-a · još Eurostat, Hrvatska pošta, OpenStreetMap</p>`,
    );
  },
  1500,
  "Kartica „Izvori podataka”: šest glavnih izdavača i čemu služe; ispod, kako su povezani.",
);

await scene(
  "Tehnička arhitektura",
  "Arhitektura je jednostavna. Svake noći program u Pythonu preuzima izvore, obrađuje ih i provjerava kvalitetu. Iz toga nastaje JSON za svaku općinu, a Next.js od njega gradi statičke stranice. Nema poslužitelja ni baze. Ako neki izvor ne radi, ostaju njegovi zadnji ispravni podaci.",
  async () => {
    const box = (b, s) => `<div class="box"><b>${b}</b><span>${s}</span></div>`;
    const arrow = `<div class="arrow" aria-hidden="true">→</div>`;
    await infoCard(
      "Tehnička arhitektura",
      `<div class="flow">${[
        box("Izvori", "API, XLSX, CSV, GeoJSON"),
        box("Python", "preuzimanje, obrada, kontrola kvalitete"),
        box("JSON", "jedna datoteka po općini, JSON Schema"),
        box("Next.js", "statičke stranice, rade i bez JavaScripta"),
        box("GitHub Pages", "javna stranica"),
      ].join(arrow)}</div>
      <p class="note">Svake noći u GitHub Actions · bez poslužitelja i baze · otvoreni kod (EUPL-1.2)</p>`,
    );
  },
  2000,
  "Kartica „Tehnička arhitektura”: Izvori → Python → JSON → Next.js → GitHub Pages.",
);

await scene(
  "Jednostavnim jezikom, i na engleskom",
  "Cijela stranica postoji i na jednostavnom jeziku, za one kojima je službeni jezik težak, te na engleskom.",
  async () => {
    // Back from the cards to the city page.
    await page.goto(site.origin + "/opcina/lepoglava/");
    await caption("Jednostavnim jezikom, i na engleskom");
    await wait(1000);
    const simple = page.getByRole("link", { name: "Jednostavni jezik" });
    await click(simple);
    await page.waitForLoadState("networkidle");
    await caption("Jednostavnim jezikom, i na engleskom");
    await wait(1500);
    await click(page.getByRole("link", { name: "English" }));
    await page.waitForLoadState("networkidle");
    await caption("Jednostavnim jezikom, i na engleskom");
  },
  1000,
  "Klik na „Obični jezik”, zatim na „English”: ista stranica u druga dva izdanja.",
);

await scene(
  "Pristupačno: WCAG 2.1 AA, i na mobitelu",
  "Radi na mobitelu, u svijetlom i tamnom načinu, i zadovoljava standard pristupačnosti WCAG 2.1 AA.",
  async () => {
    // Two phones side by side: the same page in light and dark mode.
    const phone = (scheme) =>
      `<iframe src="${site.origin}/opcina/lepoglava/" title="${scheme}"
        style="zoom:1.4;width:375px;height:540px;border:10px solid #0b0b0b;border-radius:28px;
        background:#fff;color-scheme:${scheme}"></iframe>`;
    // zoom on each phone scales the page inside it, like a phone screen held up close.
    await setPage(`<!doctype html><html lang="hr"><meta charset="utf-8">
      <body style="margin:0;height:100vh;display:flex;gap:120px;align-items:flex-start;
        justify-content:center;padding-top:24px;box-sizing:border-box;background:#eeede9;
        opacity:0;transition:opacity .4s ease-out">
        ${phone("light")}${phone("dark")}
      </body></html>`);
    // The second frame follows the dark colour scheme of the site's own tokens.
    await page
      .frames()[2]
      ?.evaluate(() =>
        document.documentElement.setAttribute("data-theme", "dark"),
      );
    // Fade in once both phones have loaded, instead of showing empty frames.
    await page.evaluate(() => (document.body.style.opacity = "1"));
    await caption("Pristupačno: WCAG 2.1 AA, i na mobitelu");
    await wait(1200);
    for (const frame of page.frames().slice(1))
      await frame.evaluate(() => scrollTo({ top: 260, behavior: "smooth" }));
  },
  1500,
  "Dva mobitela jedan uz drugi: stranica Lepoglave u svijetlom i u tamnom načinu.",
);

await scene(
  "Daljnji razvoj",
  "Sljedeći koraci su svih 556 gradova i općina u Hrvatskoj, svi ugovori od 2024. preko API-ja javne nabave, isplate za više mjesta i testiranje sa stanovnicima.",
  async () => {
    await infoCard(
      "Daljnji razvoj",
      items([
        ["Svih 556 gradova i općina", "isti program, sve županije"],
        ["Ugovori od 2024.", "službeni API javne nabave (EOJN)"],
        ["Isplate za više mjesta", "podrška za više portala na kojima ih gradovi objavljuju"],
        ["Testiranje", "sa stanovnicima i čitačima zaslona"],
      ]),
    );
  },
  2000,
  "Kartica „Daljnji razvoj”: četiri sljedeća koraka.",
);

await scene(
  "",
  "U minuti dobijete odgovor za koji biste inače pretražili desetak stranica. Danas 28 gradova i općina Varaždinske županije, a cilj je svih 556. Otvoreni podaci, otvoreni kod.",
  async () => {
    await titleCard("Moja općina u brojkama", [
      LIVE_URL.replace("https://", ""),
      "28 gradova i općina Varaždinske županije · cilj: svih 556",
      "Otvoreni podaci · otvoreni kod (EUPL-1.2)",
    ]);
  },
  2500,
  "Završna kartica: adresa stranice, opseg i licenca.",
);

// --- Output ------------------------------------------------------------------------

const video = page.video();
await context.close();
const recorded = await video.path();
const webm = path.join(outDir, "predstavljanje.webm");
renameSync(recorded, webm);
await browser.close();
site.close();

const stamp = (s, sep) => {
  const ms = Math.round(s * 1000);
  const h = String(Math.floor(ms / 3600000)).padStart(2, "0");
  const m = String(Math.floor(ms / 60000) % 60).padStart(2, "0");
  const sec = String(Math.floor(ms / 1000) % 60).padStart(2, "0");
  return `${h}:${m}:${sec}${sep}${String(ms % 1000).padStart(3, "0")}`;
};

const captioned = timeline.filter((s) => s.caption);
writeFileSync(
  path.join(outDir, "predstavljanje.srt"),
  captioned
    .map(
      (s, i) =>
        `${i + 1}\n${stamp(s.start, ",")} --> ${stamp(s.end, ",")}\n${s.caption}\n`,
    )
    .join("\n"),
);

// Which part of the presentation each scene is (the topics the datathon rules list).
const F = "Funkcionalnosti";
const PART = [
  "Problem",
  "Ciljni korisnici",
  F, F, F, F, F, F, F, F, F, F,
  "Funkcionalnosti, izvori",
  "Izvori podataka",
  "Tehnička arhitektura",
  F, F,
  "Daljnji razvoj",
  "Korisnička vrijednost",
];
if (PART.length !== timeline.length)
  throw new Error(`PART has ${PART.length} entries for ${timeline.length} scenes`);

const mmss = (s) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
writeFileSync(
  path.join(outDir, "naracija.md"),
  [
    "# Scenarij video predstavljanja",
    "",
    `Video: \`predstavljanje.mp4\` (${mmss(timeline.at(-1).end)}, 1920×1080, s natpisima na zaslonu). Natpisi su i u \`predstavljanje.srt\`.`,
    "",
    "Pravila Datathona traže da video obuhvati: opis problema, ciljne korisnike, korištene izvore podataka, funkcionalnosti, tehničku arhitekturu, korisničku vrijednost i mogućnosti daljnjeg razvoja. Uz vrijeme svake scene piše koji od tih dijelova pokriva.",
    "",
    "## Kako snimiti glas",
    "",
    "1. Pustite video bez zvuka i čitajte uz njega; svaka scena počinje u označeno vrijeme. Vremena su izračunata za normalan tempo govora, pa tekst stane bez žurbe.",
    "2. Snimajte mobitelom u tihoj prostoriji, oko 20 cm od usta. Na početku ostavite 2 sekunde tišine.",
    "3. Ako jedna snimka ne ide, snimite svaku scenu kao zasebnu datoteku (`01.m4a`, `02.m4a`…); svaka se postavi na svoje vrijeme.",
    "",
    "Video se ponovno snima iz izgrađene stranice (`web/`): `npm run build && node scripts/video.mjs ../docs/video`, pa pretvorba u MP4 (ffmpeg, H.264). Tada se i ovaj scenarij piše iznova, sa stvarnim vremenima.",
    "",
    "## Scene",
    "",
    ...timeline.flatMap((s, i) => [
      `### ${i + 1}. ${mmss(s.start)}–${mmss(s.end)} · ${PART[i]}`,
      "",
      `**Na zaslonu:** ${s.shows}`,
      "",
      ...(s.caption ? [`**Natpis:** „${s.caption}”`, ""] : []),
      `**Govor:** ${s.narration}`,
      "",
    ]),
    "## Cijeli tekst za čitanje",
    "",
    ...timeline.flatMap((s) => [`${s.narration}`, ""]),
  ].join("\n"),
);

console.log(`video: ${webm} (${mmss(now())}), ${timeline.length} scenes`);
