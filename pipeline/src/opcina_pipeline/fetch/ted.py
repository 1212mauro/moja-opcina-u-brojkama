"""Contract award notices from TED, the EU's Tenders Electronic Daily (task C1).

The new EOJN register (2024 onwards) is open only through an API that needs a key.
Every procurement above the EU thresholds is also published on TED, whose search API
is open: no key, reuse free with attribution (Commission Decision 2011/833/EU).

``POST https://api.ted.europa.eu/v3/notices/search`` (anonymous) with an expert query:
buyer OIB in scope, contract award notices (``can-standard``, ``can-social``),
published since 2024; pages of 250 notices with the fields the parser needs.

Only the search API is used. The notice pages on ted.europa.eu (including the eForms
XML) sit behind an AWS WAF that answers cloud servers such as GitHub Actions with a
JavaScript challenge, which a pipeline must not try to pass. The API's fields are flat
lists per notice, so a winner can be tied to its contract only when the notice has a
single contract; the parser keeps those (see ``parse.contracts.parse_ted_file``).

File: ``notices.jsonl``, one notice per line as returned, by publication number.
"""

import json

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.eojn import _write_if_changed, scope_buyers

SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
NOTICE_TYPES = ("can-standard", "can-social")
SINCE = "20240101"  # the old EOJN register covers everything before
PAGE_SIZE = 250
FIELDS = [
    "publication-number",
    "publication-date",
    "notice-type",
    "organisation-identifier-buyer",
    "title-proc",
    "procedure-type",
    "classification-cpv",
    "contract-identifier",
    "contract-conclusion-date",
    "tender-value",
    "tender-value-cur",
    "winner-identifier",
    "winner-name",
]


def search_query(buyer_oibs: list[str]) -> str:
    """TED expert query for award notices of the given buyers since ``SINCE``."""
    return (
        f"organisation-identifier-buyer IN ({' '.join(sorted(buyer_oibs))}) "
        f"AND notice-type IN ({' '.join(NOTICE_TYPES)}) "
        f"AND publication-date>={SINCE}"
    )


def publication_order(number: str) -> tuple[str, int]:
    """``"193551-2024"`` sorts by year, then number."""
    serial, year = number.split("-")
    return year, int(serial)


def search_notices(ctx: FetchContext, buyer_oibs: list[str]) -> list[dict]:
    """Every matching notice with ``FIELDS``, oldest first."""
    notices: dict[str, dict] = {}
    page = 1
    while True:
        response = ctx.client.post(
            SEARCH_URL,
            json={
                "query": search_query(buyer_oibs),
                "fields": FIELDS,
                "limit": PAGE_SIZE,
                "page": page,
                "paginationMode": "PAGE_NUMBER",
            },
        )
        response.raise_for_status()
        body = response.json()
        batch = body.get("notices", [])
        for notice in batch:
            notice.pop("links", None)  # URLs to every language version: noise
            notices[notice["publication-number"]] = notice
        if len(batch) < PAGE_SIZE or len(notices) >= body.get("totalNoticeCount", 0):
            break
        page += 1
    return [notices[n] for n in sorted(notices, key=publication_order)]


@fetcher("contracts_ted")
def fetch_ted(ctx: FetchContext) -> Outcome:
    buyers = scope_buyers(ctx)
    notices = search_notices(ctx, buyers["oib"].to_list())
    text = "".join(json.dumps(n, ensure_ascii=False, sort_keys=True) + "\n" for n in notices)
    file = _write_if_changed(ctx.out_dir / "notices.jsonl", text)
    return Outcome.from_downloads(
        [file], f"{len(notices)} award notices for {buyers.height} buyers"
    )
