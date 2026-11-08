# Screenshots

First-screen captures of the live design (H8), for the submission (G6). Each page is
captured at 360 px (phone), 768 px (tablet) and 1280 px (desktop), in light and dark
mode. File names are `<page>--<width>-<scheme>.png`.

| Page | Files |
|---|---|
| Home page | `home--*` |
| Lepoglava, standard Croatian | `opcina_lepoglava--*` |
| Lepoglava, simple language | `jednostavno_opcina_lepoglava--*` |
| Lepoglava, English | `en_municipality_lepoglava--*` |
| Data sources | `izvori--*` |

To capture them again after a change (from `web/`, after `npm run build`):

```bash
MSYS_NO_PATHCONV=1 node scripts/screenshots.mjs ../docs/screenshots --top / /opcina/lepoglava/ /jednostavno/opcina/lepoglava/ /en/municipality/lepoglava/ /izvori/
```

`MSYS_NO_PATHCONV=1` is needed only in Git Bash on Windows. Without `--top` the
script captures full pages, for visual QA.
