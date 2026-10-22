"""Statistics and reference files: DZS census and estimates, Eurostat LAU codes, postcodes."""

import re
import zipfile

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.links import find_links

DIRECT_SOURCES = ["dzs_population", "dzs_settlements", "dzs_estimates", "postcodes"]


def fetch_direct(ctx: FetchContext) -> Outcome:
    """Sources with a stable download URL."""
    download = ctx.client.download(ctx.source.url, ctx.source.path, ignore_parts=ctx.ignore_parts)
    if not zipfile.is_zipfile(download.path):  # every one of these is an xlsx
        raise ValueError(f"{ctx.source.url} did not return an xlsx file")
    return Outcome.from_downloads([download])


for key in DIRECT_SOURCES:
    fetcher(key)(fetch_direct)


@fetcher("lau_codes")
def fetch_lau(ctx: FetchContext) -> Outcome:
    """Newest yearly LAU list linked from Eurostat's LAU page."""
    page = ctx.client.get(ctx.source.page).text
    pattern = ctx.source.options["link_pattern"]
    by_year = {
        int(re.search(pattern, url).group(1)): url
        for url in find_links(page, pattern, ctx.source.page)
    }
    if not by_year:
        raise ValueError(f"no LAU files matching {pattern!r} on {ctx.source.page}")
    year = max(by_year)
    download = ctx.client.download(by_year[year], ctx.source.path)
    return Outcome.from_downloads([download], f"LAU {year}")
