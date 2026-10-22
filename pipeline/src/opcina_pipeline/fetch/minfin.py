"""Ministry of Finance: budget execution files and the RKP register."""

import re
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.http import Download, file_sha256
from opcina_pipeline.fetch.links import find_links

TOKEN_PATTERN = r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'


@fetcher("minfin_budget")
def fetch_budget(ctx: FetchContext) -> Outcome:
    """Newest "PR-RAS i RAS-funkc" period page -> its EURO zip -> this county's workbook."""
    options = ctx.source.options
    section = ctx.client.get(ctx.source.url).text
    periods = [
        (int(m.group(2)), urljoin(ctx.source.url, m.group(0)))
        for m in re.finditer(options["period_page_pattern"], section)
    ]
    if not periods:
        raise ValueError(f"no period pages matching {options['period_page_pattern']!r}")
    last_year, period_url = max(periods)

    zips = find_links(ctx.client.get(period_url).text, options["zip_pattern"], period_url)
    if len(zips) != 1:
        raise ValueError(f"expected one EURO zip on {period_url}, found {zips}")
    archive = ctx.client.download(zips[0], ctx.out_dir / "lokalci_euro.zip")

    county = ctx.source.path
    if archive.changed or not county.exists():
        extract_county_workbook(archive.path, ctx.scope.register_code, county)
        changed = True
    else:
        changed = False
    workbook = Download(county, changed, file_sha256(county), county.stat().st_size)
    return Outcome.from_downloads([archive, workbook], f"period ending {last_year}: {zips[0]}")


def zip_member_name(info: zipfile.ZipInfo) -> str:
    """Member names in MinFin zips are cp852 (DOS Croatian) without the UTF-8 flag."""
    if info.flag_bits & 0x800:
        return info.filename
    return info.filename.encode("cp437").decode("cp852")


def extract_county_workbook(archive: Path, county_code: str, dest: Path) -> str:
    """Copy "<NN> <County>.xlsx" out of the zip; prefer an "ispravak" (correction) if present."""
    prefix = f"{int(county_code):02d} "
    with zipfile.ZipFile(archive) as zf:
        matches = [
            info
            for info in zf.infolist()
            if Path(zip_member_name(info)).name.startswith(prefix)
            and zip_member_name(info).lower().endswith(".xlsx")
        ]
        if not matches:
            raise ValueError(f"no workbook starting with {prefix!r} in {archive.name}")
        matches.sort(key=lambda info: "ispravak" not in zip_member_name(info).lower())
        chosen = matches[0]
        tmp = dest.with_name(dest.name + ".part")
        with zf.open(chosen) as src, tmp.open("wb") as out:
            while chunk := src.read(1 << 20):
                out.write(chunk)
        tmp.replace(dest)
        return zip_member_name(chosen)


@fetcher("minfin_budget_users")
def fetch_register(ctx: FetchContext) -> Outcome:
    """The RKPFI portal's own Export button: a form POST with an anti-forgery token."""
    page = ctx.client.get(ctx.source.page).text
    token = re.search(TOKEN_PATTERN, page)
    if not token:
        raise ValueError("no __RequestVerificationToken on the RKP register page")
    download = ctx.client.download(
        ctx.source.url,
        ctx.source.path,
        method="POST",
        ignore_parts=ctx.ignore_parts,
        data={
            "__RequestVerificationToken": token.group(1),
            "Year": str(date.today().year),
            "Active": "Active",
        },
    )
    if not zipfile.is_zipfile(download.path):
        raise ValueError("RKP export did not return an xlsx file")
    return Outcome.from_downloads([download])
