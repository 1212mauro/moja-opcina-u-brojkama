"""Polite HTTP client shared by all fetchers.

- Identifies the project in the User-Agent.
- Waits at least ``min_interval`` seconds between requests to the same host.
- Retries timeouts, 429 and 5xx with exponential backoff, honouring Retry-After.
- Downloads stream to a temporary file and replace the target atomically, and use
  ETag / Last-Modified so unchanged files are not downloaded again.
"""

import hashlib
import json
import time
import zipfile
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

USER_AGENT = "moja-opcina-u-brojkama/0.1 (+https://github.com/1212mauro/moja-opcina-u-brojkama)"
RETRY_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Download:
    path: Path
    changed: bool  # False when the server answered 304 Not Modified
    sha256: str
    bytes: int


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Packaging parts of xlsx/ods files: metadata, relationship ids, generator-specific files.
PACKAGING_PREFIXES = ("docProps/", "package/", "_rels/", "meta.xml")


def content_fingerprint(path: Path, ignore_parts: frozenset[str] = frozenset()) -> str:
    """Hash of what a file says, for change detection.

    Workbooks generated on request (RKP export, Pošta list) carry fresh creation
    times and random relationship ids on every download; packaging parts, plus any
    ``ignore_parts`` a source names, are left out so unchanged data stays unchanged.
    """
    if path.suffix.lower() not in {".xlsx", ".ods"} or not zipfile.is_zipfile(path):
        return file_sha256(path)
    digest = hashlib.sha256()
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if name.startswith(PACKAGING_PREFIXES) or name in ignore_parts:
                continue
            digest.update(name.encode())
            digest.update(zf.read(name))
    return digest.hexdigest()


class ConditionalCache:
    """ETag / Last-Modified per URL, persisted as JSON next to the raw data."""

    def __init__(self, path: Path):
        self.path = path
        self._entries: dict[str, dict] = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        )

    def headers_for(self, url: str, dest: Path) -> dict[str, str]:
        entry = self._entries.get(url)
        if not entry or not dest.exists():
            return {}
        headers = {}
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]
        return headers

    def store(self, url: str, response: httpx.Response) -> None:
        self._entries[url] = {
            "etag": response.headers.get("etag"),
            "last_modified": response.headers.get("last-modified"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._entries, indent=2), encoding="utf-8")


class PoliteClient:
    def __init__(
        self,
        cache: ConditionalCache | None = None,
        min_interval: float = 1.0,
        timeout: float = 120.0,
        retries: int = 4,
        host_intervals: dict[str, float] | None = None,
        transport: httpx.BaseTransport | None = None,  # tests pass an httpx.MockTransport
        backoff: float = 1.0,
    ):
        self.cache = cache
        self.min_interval = min_interval
        self.host_intervals = host_intervals or {}
        self.retries = retries
        self.backoff = backoff
        self._last_request: dict[str, float] = {}
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    @property
    def cookies(self) -> httpx.Cookies:
        return self._http.cookies

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "PoliteClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _throttle(self, url: str) -> None:
        host = urlsplit(url).hostname or ""
        interval = self.host_intervals.get(host, self.min_interval)
        wait = self._last_request.get(host, 0.0) + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request[host] = time.monotonic()

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send a request with throttling and retries; raises on a final 4xx/5xx."""
        for attempt in range(self.retries + 1):
            self._throttle(url)
            try:
                response = self._http.request(method, url, **kwargs)
            except httpx.TransportError:
                if attempt == self.retries:
                    raise
                time.sleep(self.backoff * 2**attempt)
                continue
            if response.status_code in RETRY_STATUSES and attempt < self.retries:
                time.sleep(_retry_after(response) or self.backoff * 2**attempt * 5)
                continue
            if response.status_code != 304:
                response.raise_for_status()
            return response
        raise AssertionError("unreachable")

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def download(
        self,
        url: str,
        dest: Path,
        method: str = "GET",
        ignore_parts: frozenset[str] = frozenset(),
        **kwargs,
    ) -> Download:
        """Stream ``url`` to ``dest``; skip the body if the server says it has not changed.

        ``ignore_parts``: workbook parts that change on every download (e.g. an export
        timestamp sheet) and must not count as a data change.
        """
        headers = dict(kwargs.pop("headers", {}) or {})
        conditional = self.cache is not None and method == "GET"
        if conditional:
            headers.update(self.cache.headers_for(url, dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        # Servers without ETag/Last-Modified (and POST exports) still report "unchanged"
        # when the new body is byte-identical to what we already have.
        previous = content_fingerprint(dest, ignore_parts) if dest.exists() else None

        for attempt in range(self.retries + 1):
            self._throttle(url)
            try:
                with self._http.stream(method, url, headers=headers, **kwargs) as response:
                    if response.status_code == 304:
                        return Download(dest, False, file_sha256(dest), dest.stat().st_size)
                    if response.status_code in RETRY_STATUSES and attempt < self.retries:
                        time.sleep(_retry_after(response) or self.backoff * 2**attempt * 5)
                        continue
                    response.raise_for_status()
                    with tmp.open("wb") as f:
                        for chunk in response.iter_bytes(1 << 20):
                            f.write(chunk)
                    tmp.replace(dest)
                    if conditional:
                        self.cache.store(url, response)
                    changed = content_fingerprint(dest, ignore_parts) != previous
                    return Download(dest, changed, file_sha256(dest), dest.stat().st_size)
            except httpx.TransportError:
                tmp.unlink(missing_ok=True)
                if attempt == self.retries:
                    raise
                time.sleep(self.backoff * 2**attempt)
        raise AssertionError("unreachable")


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    if value.isdigit():
        return float(value)
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
    except (TypeError, ValueError):
        return None
