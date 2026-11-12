"""Tests for the Al Kamel client (URL building + download, offline-only)."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from endurancepy.alkamel.client import (
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT,
    build_results_url,
    download,
)
from endurancepy.cache import Cache
from endurancepy.exceptions import SessionNotAvailableError


def test_build_results_url_basic() -> None:
    url = build_results_url(
        "fiawec.alkamelsystems.com",
        "13_2024",
        "01_LOSAIL",
        "581_FR Middle East Championship",
        "202502261915_Free Practice",
        "23_Analysis_Free Practice.CSV",
    )
    assert url == (
        "https://fiawec.alkamelsystems.com/Results/13_2024/01_LOSAIL/"
        "581_FR%20Middle%20East%20Championship/202502261915_Free%20Practice/"
        "23_Analysis_Free%20Practice.CSV"
    )


def test_build_results_url_with_hour() -> None:
    url = build_results_url(
        "fiawec.alkamelsystems.com",
        "08_2018-2019",
        "07_SPA FRANCORCHAMPS",
        "267_FIA WEC",
        "201905041330_Race",
        "23_Analysis_Race_Hour 6.CSV",
        hour=6,
    )
    assert url == (
        "https://fiawec.alkamelsystems.com/Results/08_2018-2019/"
        "07_SPA%20FRANCORCHAMPS/267_FIA%20WEC/201905041330_Race/Hour%206/"
        "23_Analysis_Race_Hour%206.CSV"
    )


@pytest.mark.parametrize("scheme", ["https", "http"])
def test_download_uses_cache_session(
    monkeypatch: pytest.MonkeyPatch, scheme: str
) -> None:
    captured: dict[str, object] = {}

    class _FakeSession(requests.Session):
        def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:  # type: ignore[override]
            captured.update(kwargs)
            captured["url"] = url
            captured["method"] = method
            response = requests.Response()
            response.status_code = 200
            response._content = b"payload"
            return response

    monkeypatch.setattr(
        Cache, "requests_session", classmethod(lambda cls: _FakeSession())
    )

    assert download(f"{scheme}://example.test/file.CSV") == b"payload"
    assert captured["url"] == f"{scheme}://example.test/file.CSV"
    assert captured["headers"] == DEFAULT_HEADERS
    assert captured["timeout"] == REQUEST_TIMEOUT
    assert captured["allow_redirects"] is False
    assert captured["method"] == "GET"


@pytest.mark.parametrize("status", [301, 302, 307, 401, 403, 404, 500])
def test_http_errors_and_redirects_stop(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    calls = []

    def request(
        self: requests.Session, *args: object, **kwargs: object
    ) -> requests.Response:
        calls.append((args, kwargs))
        response = requests.Response()
        response.status_code = status
        response.url = "https://example.test/data"
        return response

    monkeypatch.setattr(requests.Session, "request", request)
    Cache.set_disabled()
    with pytest.raises(SessionNotAvailableError):
        download("https://example.test/data")
    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False


@pytest.mark.parametrize("body", [b"<html>Login</html>", b"[]", b"null"])
def test_invalid_json_stops(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    def request(
        self: requests.Session, *args: object, **kwargs: object
    ) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response._content = body
        return response

    monkeypatch.setattr(requests.Session, "request", request)
    Cache.set_disabled()
    with pytest.raises(SessionNotAvailableError):
        from endurancepy.alkamel.client import download_json

        download_json("https://example.test/manifest.json")


def test_cached_post_and_get_are_anonymous(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from endurancepy.alkamel.client import download_json

    requests_sent: list[requests.PreparedRequest] = []

    class Adapter(requests.adapters.BaseAdapter):
        def send(  # type: ignore[override]
            self, request: requests.PreparedRequest, **kwargs: Any
        ) -> requests.Response:
            requests_sent.append(request)
            response = requests.Response()
            response.status_code = 200
            response._content = b'{"public": true}'
            response.headers["Content-Type"] = "application/json"
            response.request = request
            response.url = str(request.url)
            # requests-cache normally obtains these from the urllib3 response.
            import io

            from urllib3.response import HTTPResponse

            response.raw = HTTPResponse(body=io.BytesIO(response.content), status=200)
            return response

        def close(self) -> None:
            pass

    Cache.enable_cache(tmp_path)
    session = Cache.requests_session()
    session.mount("https://", Adapter())
    session.auth = ("user", "secret")
    session.cookies.set("session", "secret")
    session.headers["Authorization"] = "secret"
    for _ in range(2):
        assert download_json(
            "https://example.test/settings", payload={"url": "test.alkamelcloud.com"}
        ) == {"public": True}
        assert download_json("https://example.test/results.json") == {"public": True}
    assert len(requests_sent) == 2  # GET and POST both reused from requests-cache
    for request in requests_sent:
        assert request.headers["User-Agent"] == DEFAULT_HEADERS["User-Agent"]
        assert (
            not {"Authorization", "Cookie", "Origin", "Referer"}
            & request.headers.keys()
        )
    assert session.trust_env is False
