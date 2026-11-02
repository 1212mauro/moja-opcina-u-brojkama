"""Datasets on data.gov.hr (CKAN): school and kindergarten registries, municipal registers."""

from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.http import Download
from opcina_pipeline.fetch.links import safe_url
from opcina_pipeline.text import slugify

CKAN_API = "https://data.gov.hr/ckan/api/3/action/package_show"
CKAN_SOURCES = ["schools_primary", "schools_secondary", "kindergartens"]


def _suffix(resource: dict) -> str:
    return PurePosixPath(urlsplit(resource["url"]).path).suffix.lower()


def resource_filename(resource: dict) -> str:
    """Stable local name: slug of the resource name + the URL's extension."""
    suffix = _suffix(resource) or "." + resource.get("format", "bin").lower()
    return f"{slugify(resource.get('name') or resource['id'])}{suffix}"


def _wanted(resource: dict, formats: set[str]) -> bool:
    # Publishers mislabel formats (an .xlsx tagged "XML"), so the file extension counts too.
    labels = {(resource.get("format") or "").upper(), _suffix(resource).lstrip(".").upper()}
    return not formats or bool(labels & formats)


def download_dataset(ctx: FetchContext, dataset: str, folder: Path) -> tuple[list[Download], str]:
    """Every resource of ``dataset`` in the configured formats, into ``folder``."""
    formats = {f.upper() for f in ctx.source.options.get("formats", [])}
    package = ctx.client.get(CKAN_API, params={"id": dataset}).json()
    if not package.get("success"):
        raise ValueError(f"CKAN package_show failed for {dataset}: {package.get('error')}")

    resources = [r for r in package["result"]["resources"] if _wanted(r, formats)]
    if not resources:
        raise ValueError(f"no {sorted(formats)} resources in dataset {dataset}")

    names = [resource_filename(r) for r in resources]
    # Publishers sometimes upload the same file twice under one name; the id keeps both.
    names = [
        name if names.count(name) == 1 else f"{r['id'][:8]}-{name}"
        for r, name in zip(resources, names, strict=True)
    ]
    folder.mkdir(parents=True, exist_ok=True)
    files = [
        ctx.client.download(safe_url(r["url"]), folder / name, ignore_parts=ctx.ignore_parts)
        for r, name in zip(resources, names, strict=True)
    ]
    modified = max((r.get("last_modified") or r.get("created") or "") for r in resources)
    return files, modified[:10]


def fetch_ckan_dataset(ctx: FetchContext) -> Outcome:
    """One dataset (``ckan_dataset`` in sources.toml)."""
    files, modified = download_dataset(ctx, ctx.source.options["ckan_dataset"], ctx.out_dir)
    return Outcome.from_downloads(files, f"{len(files)} resources, last modified {modified}")


for key in CKAN_SOURCES:
    fetcher(key)(fetch_ckan_dataset)


@fetcher("contracts_municipal")
def fetch_municipal_registers(ctx: FetchContext) -> Outcome:
    """Several publishers' datasets (``datasets``), each into ``<publisher OIB>/``."""
    datasets = ctx.source.options["datasets"]
    files: list[Download] = []
    for dataset in datasets:
        folder = ctx.out_dir / dataset["oib"]
        got, _ = download_dataset(ctx, dataset["ckan_dataset"], folder)
        # A resource the publisher removed or renamed must not be parsed again.
        current = {f.path.name for f in got}
        for stale in folder.iterdir():
            if stale.is_file() and stale.name not in current:
                stale.unlink()
        files += got
    return Outcome.from_downloads(files, f"{len(files)} files from {len(datasets)} publishers")
