"""Contract award notices from TED, the EU's Tenders Electronic Daily (task C1).

The new EOJN register (2024 onwards) is open only through an API that needs a key.
Every procurement above the EU thresholds is also published on TED, which is open:
no key, reuse free with attribution (Commission Decision 2011/833/EU), and robots.txt
allows the notice pages. So TED covers the largest new contracts without asking anyone.

1. ``POST https://api.ted.europa.eu/v3/notices/search`` (anonymous) with an expert
   query: buyer OIB in scope, contract award notices (``can-standard``,
   ``can-social``), published since 2024. Pages of 250 publication numbers.
2. ``GET https://ted.europa.eu/en/notice/<publication number>/xml`` for each notice
   not yet on disk: the eForms XML, which links each lot result to its winning tender,
   signed contract and supplier exactly (the search API's flat fields cannot be lined
   up per lot). A published notice never changes; corrections are new notices.
   Every file must parse as XML: TED has answered with an empty body, and such a
   file is deleted (and fetched again next run) rather than kept forever.

Files: ``notices/<publication number>.xml``.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.eojn import scope_buyers
from opcina_pipeline.fetch.http import Download, file_sha256

SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
NOTICE_XML_URL = "https://ted.europa.eu/en/notice/{number}/xml"
NOTICE_TYPES = ("can-standard", "can-social")
SINCE = "20240101"  # the old EOJN register covers everything before
PAGE_SIZE = 250


def search_query(buyer_oibs: list[str]) -> str:
    """TED expert query for award notices of the given buyers since ``SINCE``."""
    return (
        f"organisation-identifier-buyer IN ({' '.join(sorted(buyer_oibs))}) "
        f"AND notice-type IN ({' '.join(NOTICE_TYPES)}) "
        f"AND publication-date>={SINCE}"
    )


def search_notices(ctx: FetchContext, buyer_oibs: list[str]) -> list[str]:
    """Publication numbers of every matching notice, oldest first."""
    numbers: list[str] = []
    page = 1
    while True:
        response = ctx.client.post(
            SEARCH_URL,
            json={
                "query": search_query(buyer_oibs),
                "fields": ["publication-number"],
                "limit": PAGE_SIZE,
                "page": page,
                "paginationMode": "PAGE_NUMBER",
            },
        )
        response.raise_for_status()
        body = response.json()
        batch = [n["publication-number"] for n in body.get("notices", [])]
        numbers.extend(batch)
        if len(batch) < PAGE_SIZE or len(numbers) >= body.get("totalNoticeCount", 0):
            break
        page += 1
    # "193551-2024": sort by year, then number.
    return sorted(set(numbers), key=lambda n: (n.split("-")[1], int(n.split("-")[0])))


@fetcher("contracts_ted")
def fetch_ted(ctx: FetchContext) -> Outcome:
    buyers = scope_buyers(ctx)
    numbers = search_notices(ctx, buyers["oib"].to_list())
    folder = ctx.out_dir / "notices"
    folder.mkdir(exist_ok=True)
    files, broken = [], []
    for number in numbers:
        dest = folder / f"{number}.xml"
        if _is_xml(dest):
            # Notices never change; listed anyway so the run log names every input.
            files.append(Download(dest, False, file_sha256(dest), dest.stat().st_size))
            continue
        download = ctx.client.download(NOTICE_XML_URL.format(number=number), dest)
        if _is_xml(dest):
            files.append(download)
        else:
            dest.unlink(missing_ok=True)
            broken.append(number)
    new = sum(f.changed for f in files)
    message = f"{len(numbers)} award notices for {buyers.height} buyers, {new} new"
    if broken:
        message += f"; not valid XML, retried next run: {', '.join(broken)}"
    return Outcome.from_downloads(files, message)


def _is_xml(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        ET.parse(path)
    except ET.ParseError:
        return False
    return True
