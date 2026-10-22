"""Datasets on data.gov.hr (CKAN): school and kindergarten registries, municipal registers."""

from pathlib import PurePosixPath
from urllib.parse import urlsplit

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.links import safe_url
from opcina_pipeline.text import slugify

CKAN_API = "https://data.gov.hr/ckan/api/3/action/package_show"
CKAN_SOURCES = ["schools_primary", "schools_secondary", "kindergartens", "contracts_ivanec"]


def resource_filename(resource: dict) -> str:
    """Stable local name: slug of the resource name + the URL's extension."""
    suffix = PurePosixPath(urlsplit(resource["url"]).path).suffix.lower()
    if not suffix:
        suffix = "." + resource.get("format", "bin").lower()
    return f"{slugify(resource.get('name') or resource['id'])}{suffix}"


def fetch_ckan_dataset(ctx: FetchContext) -> Outcome:
    """Every resource of the dataset in the configured formats (``formats`` in sources.toml)."""
    dataset = ctx.source.options["ckan_dataset"]
    formats = {f.upper() for f in ctx.source.options.get("formats", [])}
    package = ctx.client.get(CKAN_API, params={"id": dataset}).json()
    if not package.get("success"):
        raise ValueError(f"CKAN package_show failed for {dataset}: {package.get('error')}")

    resources = [
        r
        for r in package["result"]["resources"]
        if not formats or (r.get("format") or "").upper() in formats
    ]
    if not resources:
        raise ValueError(f"no {sorted(formats)} resources in dataset {dataset}")

    names = [resource_filename(r) for r in resources]
    # Publishers sometimes upload the same file twice under one name; the id keeps both.
    names = [
        name if names.count(name) == 1 else f"{r['id'][:8]}-{name}"
        for r, name in zip(resources, names, strict=True)
    ]
    files = [
        ctx.client.download(safe_url(r["url"]), ctx.out_dir / name, ignore_parts=ctx.ignore_parts)
        for r, name in zip(resources, names, strict=True)
    ]
    modified = max((r.get("last_modified") or r.get("created") or "") for r in resources)
    return Outcome.from_downloads(files, f"{len(files)} resources, last modified {modified[:10]}")


for key in CKAN_SOURCES:
    fetcher(key)(fetch_ckan_dataset)
