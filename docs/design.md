# Frontend design (section H)

The MVP pages work, are accessible and read correctly without JavaScript. Section H is about making them **easy to use at a glance**: getting a resident to their town and to an answer in under a minute (SPEC's 60-second target, task G1).

## Principles

- **Keep the system.** The tokens in `web/src/app/globals.css` are good and stay: one brand blue, warm neutrals, the 4–48 px spacing scale, the 14–32 px type scale and the contrast-checked dark mode. The redesign changes layout and hierarchy, not the palette.
- **One primary action per page.** On the home page that is finding your town. On a municipality page it is reading the key figures, then jumping to a section.
- **Nothing depends on JavaScript.** Search stays a progressive enhancement over the full list. Navigation is plain links.
- **Accessibility does not regress.** axe-core stays at 0 violations in both colour schemes. Every scrollable region is keyboard-reachable. Focus is always visible.

## Home page

Desktop (≥ 64rem):

```
┌──────────────────────────────────────────────────────────────────────┐
│ Moja općina u brojkama          Početna  Kako računamo  Izvori   EN  │
├──────────────────────────────────────────┬───────────────────────────┤
│ Pronađite svoju općinu ili grad          │ ┌───────────────────────┐ │
│ Za svaku općinu i grad pokazujemo …      │ │        county         │ │
│ ┌──────────────────────────────────────┐ │ │         map           │ │
│ │ Naziv ili poštanski broj             │ │ │      (sticky)         │ │
│ │ [ Lepoglava…                       ] │ │ └───────────────────────┘ │
│ │ Rezultata: 28                        │ │  Karta: kliknite grad …  │
│ └──────────────────────────────────────┘ │                           │
│ Naziv          Vrsta   Stanovnika  Pošt. │                           │
│ Bednja         Općina      3.254   4225… │                           │
│ …                                        │                           │
└──────────────────────────────────────────┴───────────────────────────┘
```

Phone (375 px): the title, intro and search come first, then the list. The map comes last, because a list is quicker to use on a small screen than a small map.

## Municipality page

Desktop (≥ 64rem):

```
┌──────────────────────────────────────────────────────────────────────┐
│ Početna › Varaždinska županija › Lepoglava                           │
│ ┌──────────────────────────────────────────────┬───────────────────┐ │
│ │ GRAD                                         │   locator map     │ │
│ │ Lepoglava                                    │   (this unit in   │ │
│ │ Varaždinska županija · 6.653 stanovnika      │    blue)          │ │
│ ├──────────────┬──────────────┬────────────────┴───────────────────┤ │
│ │ Prihodi 2025 │ Rashodi 2025 │ Ugovori javne nabave               │ │
│ │ 5,7 mil. €   │ 5,6 mil. €   │ 412                                │ │
│ │ 862 €/st.    │ 838 €/st.    │ od 2. 1. 2018.                     │ │
│ └──────────────┴──────────────┴────────────────────────────────────┘ │
├────────────────┬─────────────────────────────────────────────────────┤
│ Na ovoj        │ ┌ Proračun ─────────────────────────────────────┐   │
│ stranici       │ │ …                                             │   │
│ • Proračun     │ └───────────────────────────────────────────────┘   │
│ • Usporedba    │ ┌ Usporedba sa sličnima ────────────────────────┐   │
│ • Javna nabava │ │ …                                             │   │
│ • Isplate      │                                                     │
│ • Ustanove     │                                                     │
│ • Izvori       │                                                     │
│   (sticky)     │                                                     │
└────────────────┴─────────────────────────────────────────────────────┘
```

Phone: the header card stacks (name, then key figures in two columns, then the map). "Na ovoj stranici" becomes a row of chips that scrolls sideways. Wide tables (contracts, sources) scroll sideways inside their card, with a fade at the edge that shows there is more. They are no longer squeezed into broken lines.

## Components

| Component | Change |
| --- | --- |
| Header card | Name, type, county and population on the left, the locator map on the right (stacked on phones). One surface instead of four loose blocks. |
| Key figures | Larger tiles in one row; the value at 32 px, the per-resident figure under it. Later (H5): a comparison with similar units ("12 % više od prosjeka sličnih"). |
| Section navigation | A sticky sidebar list on desktop, a scrollable chip row on phones. Same links, same anchors. |
| Tables in cards | A keyboard-focusable scroll region (`role="region"`, `tabindex="0"`, labelled by the figure title). Tables with 4 or more columns get a minimum width and scroll instead of squeezing. Edge fades show the overflow. |
| Search | Moves to the top of the home page as the main action, inside a card. |

## Out of scope for now

- New colours, a new typeface, illustrations.
- Changing charts: they already follow the data-viz rules (one value axis, a summary sentence, a table behind every chart).
