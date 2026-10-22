"""Finding download links in HTML and XML pages."""

import html
import re
from urllib.parse import quote, urljoin, urlsplit, urlunsplit


def find_links(page: str, pattern: str, base_url: str) -> list[str]:
    """Absolute URLs of every match of ``pattern`` in ``page``, in page order, without repeats."""
    seen: dict[str, None] = {}
    for match in re.finditer(pattern, page):
        seen[safe_url(urljoin(base_url, html.unescape(match.group(0))))] = None
    return list(seen)


def safe_url(url: str) -> str:
    """Percent-encode spaces and non-ASCII characters in the path ("Lokalci FINALI 2019.zip")."""
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=quote(parts.path, safe="/%()")))
