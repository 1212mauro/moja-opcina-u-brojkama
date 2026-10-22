import io
import zipfile

import httpx
import pytest

from opcina_pipeline.fetch.http import ConditionalCache, PoliteClient, content_fingerprint
from opcina_pipeline.fetch.links import find_links, safe_url


def client_for(handler, tmp_path=None) -> PoliteClient:
    cache = ConditionalCache(tmp_path / "cache.json") if tmp_path else None
    return PoliteClient(
        cache=cache, min_interval=0, backoff=0, transport=httpx.MockTransport(handler)
    )


def test_conditional_download_reports_unchanged_on_304(tmp_path):
    seen_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("if-none-match"))
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, content=b"data", headers={"ETag": '"v1"'})

    with client_for(handler, tmp_path) as client:
        first = client.download("https://example.org/f.csv", tmp_path / "f.csv")
        second = client.download("https://example.org/f.csv", tmp_path / "f.csv")

    assert first.changed and not second.changed
    assert seen_headers == [None, '"v1"']
    assert (tmp_path / "f.csv").read_bytes() == b"data"


def test_identical_body_without_etag_is_unchanged(tmp_path):
    with client_for(lambda r: httpx.Response(200, content=b"same")) as client:
        assert client.download("https://example.org/a", tmp_path / "a").changed
        assert not client.download("https://example.org/a", tmp_path / "a").changed


def test_retries_server_errors_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503 if len(calls) < 3 else 200, text="ok")

    with client_for(handler) as client:
        assert client.get("https://example.org/").text == "ok"
    assert len(calls) == 3


def test_gives_up_after_retries():
    with client_for(lambda r: httpx.Response(500)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            client.get("https://example.org/")


def test_failed_download_keeps_previous_file(tmp_path):
    target = tmp_path / "keep.csv"
    target.write_bytes(b"last good")
    with client_for(lambda r: httpx.Response(404)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            client.download("https://example.org/gone", target)
    assert target.read_bytes() == b"last good"


def xlsx_bytes(sheet: str, created: str, rel_id: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
        zf.writestr("xl/worksheets/sheet2.xml", f"<exported>{created}</exported>")
        zf.writestr("docProps/core.xml", f"<created>{created}</created>")
        zf.writestr("_rels/.rels", f'<Relationship Id="{rel_id}"/>')
    return buffer.getvalue()


def test_fingerprint_ignores_packaging_and_named_parts(tmp_path):
    a, b, c = tmp_path / "a.xlsx", tmp_path / "b.xlsx", tmp_path / "c.xlsx"
    a.write_bytes(xlsx_bytes("<row>1</row>", "2026-10-22T10:00", "R1"))
    b.write_bytes(xlsx_bytes("<row>1</row>", "2026-10-23T10:00", "R2"))
    c.write_bytes(xlsx_bytes("<row>2</row>", "2026-10-22T10:00", "R1"))
    ignore = frozenset({"xl/worksheets/sheet2.xml"})

    assert content_fingerprint(a, ignore) == content_fingerprint(b, ignore)
    assert content_fingerprint(a) != content_fingerprint(b)  # sheet2 differs
    assert content_fingerprint(a, ignore) != content_fingerprint(c, ignore)


def test_find_links_resolves_and_encodes():
    page = """<a href='/docs/Lokalci FINALI 2019 2024 EURO.zip'>zip</a>
              <a href="/docs/Lokalci FINALI 2019 2024 EURO.zip">again</a>
              <a href="https://other.org/x.pdf">pdf</a>"""
    assert find_links(page, r"/docs/[^'\"]+\.zip", "https://mfin.gov.hr/page/1") == [
        "https://mfin.gov.hr/docs/Lokalci%20FINALI%202019%202024%20EURO.zip"
    ]
    assert safe_url("https://a.hr/x/Ž b.ods") == "https://a.hr/x/%C5%BD%20b.ods"
