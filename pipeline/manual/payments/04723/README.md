# Grad Varaždin: cleaned monthly payments

Written by `opcina import-varazdin` (or any local `opcina fetch payments`) from the CSV
exports saved by hand in `data/inbox/varazdin/`. One file per month, `YYYY-MM.csv`, with
only what the site publishes: no names or OIBs of individuals, no descriptions.

Commit new files here and push; the nightly run copies them into `data/raw/payments/04723/`.
The routine is in `docs/varazdin-payments.md`.
