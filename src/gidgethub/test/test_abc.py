import asyncio
import datetime
import json
import types

import pytest

from .. import RedirectionException
from .. import abc as gh_abc
from .. import sansio


class MockGitHubAPI(gh_abc.GitHubAPI):

    DEFAULT_HEADERS = {"x-ratelimit-limit": "2", "x-ratelimit-remaining": "1",
                       "x-ratelimit-reset": "0",
                       "content-type": "application/json"}

    def __init__(self, status_code=200, headers=DEFAULT_HEADERS, body=b'', *,
                 cache=None):
        self.response_code = status_code
        self.response_headers = headers
        self.response_body = body
        super().__init__("test_abc", oauth_token="oauth token", cache=cache)

    async def _request(self, method, url, headers, body=b''):
        """Make an HTTP request."""
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        response_headers = self.response_headers.copy()
        try:
            # Don't loop forever.
            del self.response_headers["link"]
        except KeyError:
            pass
        return self.response_code, response_headers, self.response_body

    async def sleep(self, seconds):  # pragma: no cover
        """Sleep for the specified number of seconds."""
        self.slept = seconds


@pytest.mark.asyncio
async def test_url_formatted():
    """The URL is appropriately formatted."""
    gh = MockGitHubAPI()
    await gh._make_request("GET", "/users/octocat/following{/other_user}",
                           {"other_user": "brettcannon"}, "",
                           sansio.accept_format())
    assert gh.url == "https://api.github.com/users/octocat/following/brettcannon"


@pytest.mark.asyncio
async def test_headers():
    """Appropriate headers are created."""
    accept = sansio.accept_format()
    gh = MockGitHubAPI()
    await gh._make_request("GET", "/rate_limit", {}, "", accept)
    assert gh.headers["user-agent"] == "test_abc"
    assert gh.headers["accept"] == accept
    assert gh.headers["authorization"] == "token oauth token"


@pytest.mark.asyncio
async def test_rate_limit_set():
    """The rate limit is updated after receiving a response."""
    rate_headers = {"x-ratelimit-limit": "42", "x-ratelimit-remaining": "1",
                    "x-ratelimit-reset": "0"}
    gh = MockGitHubAPI(headers=rate_headers)
    await gh._make_request("GET", "/rate_limit", {}, "", sansio.accept_format())
    assert gh.rate_limit.limit == 42


@pytest.mark.asyncio
async def test_decoding():
    """Test that appropriate decoding occurs."""
    original_data = {"hello": "world"}
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=utf-8"
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(original_data).encode("utf8"))
    data, _ = await gh._make_request("GET", "/rate_limit", {}, '',
                                          sansio.accept_format())
    assert data == original_data


@pytest.mark.asyncio
async def test_more():
    """The 'next' link is returned appropriately."""
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['link'] = ("<https://api.github.com/fake?page=2>; "
                       "rel=\"next\"")
    gh = MockGitHubAPI(headers=headers)
    _, more = await gh._make_request("GET", "/fake", {}, "",
                                          sansio.accept_format())
    assert more == "https://api.github.com/fake?page=2"


@pytest.mark.asyncio
async def test_getitem():
    original_data = {"hello": "world"}
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=UTF-8"
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(original_data).encode("utf8"))
    data = await gh.getitem("/fake")
    assert gh.method == "GET"
    assert data == original_data


@pytest.mark.asyncio
async def test_getiter():
    """Test that getiter() returns an async iterable as well as URI expansion."""
    original_data = [1, 2]
    next_url = "https://api.github.com/fake{/extra}?page=2"
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=UTF-8"
    headers["link"] = f'<{next_url}>; rel="next"'
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(original_data).encode("utf8"))
    data = []
    async for item in gh.getiter("/fake", {"extra": "stuff"}):
        data.append(item)
    assert gh.method == "GET"
    assert gh.url == "https://api.github.com/fake/stuff?page=2"
    assert len(data) == 4
    assert data[0] == 1
    assert data[1] == 2
    assert data[2] == 1
    assert data[3] == 2


@pytest.mark.asyncio
async def test_post():
    send = [1, 2, 3]
    send_json = json.dumps(send).encode("utf-8")
    receive = {"hello": "world"}
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=utf-8"
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(receive).encode("utf-8"))
    data = await gh.post("/fake", data=send)
    assert gh.method == "POST"
    assert gh.headers['content-type'] == "application/json; charset=utf-8"
    assert gh.body == send_json
    assert gh.headers['content-length'] == str(len(send_json))


@pytest.mark.asyncio
async def test_patch():
    send = [1, 2, 3]
    send_json = json.dumps(send).encode("utf-8")
    receive = {"hello": "world"}
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=utf-8"
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(receive).encode("utf-8"))
    data = await gh.patch("/fake", data=send)
    assert gh.method == "PATCH"
    assert gh.headers['content-type'] == "application/json; charset=utf-8"
    assert gh.body == send_json
    assert gh.headers['content-length'] == str(len(send_json))


@pytest.mark.asyncio
async def test_put():
    send = [1, 2, 3]
    send_json = json.dumps(send).encode("utf-8")
    receive = {"hello": "world"}
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=utf-8"
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(receive).encode("utf-8"))
    data = await gh.put("/fake", data=send)
    assert gh.method == "PUT"
    assert gh.headers['content-type'] == "application/json; charset=utf-8"
    assert gh.body == send_json
    assert gh.headers['content-length'] == str(len(send_json))


@pytest.mark.asyncio
async def test_delete():
    send = [1, 2, 3]
    send_json = json.dumps(send).encode("utf-8")
    receive = {"hello": "world"}
    headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
    headers['content-type'] = "application/json; charset=utf-8"
    gh = MockGitHubAPI(headers=headers,
                       body=json.dumps(receive).encode("utf-8"))
    data = await gh.delete("/fake", data=send)
    assert gh.method == "DELETE"
    assert gh.headers['content-type'] == "application/json; charset=utf-8"
    assert gh.body == send_json
    assert gh.headers['content-length'] == str(len(send_json))


class TestCache:

    @pytest.mark.asyncio
    async def test_if_none_match_sent(self):
        etag = "12345"
        cache = {"https://api.github.com/fake": (etag, None, "hi", None)}
        gh = MockGitHubAPI(cache=cache)
        await gh.getitem("/fake")
        assert "if-none-match" in gh.headers
        assert gh.headers["if-none-match"] == etag


    @pytest.mark.asyncio
    async def test_etag_received(self):
        cache = {}
        etag = "12345"
        headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
        headers["etag"] = etag
        gh = MockGitHubAPI(200, headers, b'42', cache=cache)
        data = await gh.getitem("/fake")
        url = "https://api.github.com/fake"
        assert url in cache
        assert cache[url] == (etag, None, 42, None)
        assert data == cache[url][2]

    @pytest.mark.asyncio
    async def test_if_modified_since_sent(self):
        last_modified = "12345"
        cache = {"https://api.github.com/fake": (None, last_modified, "hi", None)}
        gh = MockGitHubAPI(cache=cache)
        await gh.getitem("/fake")
        assert "if-modified-since" in gh.headers
        assert gh.headers["if-modified-since"] == last_modified

    @pytest.mark.asyncio
    async def test_last_modified_received(self):
        cache = {}
        last_modified = "12345"
        headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
        headers["last-modified"] = last_modified
        gh = MockGitHubAPI(200, headers, b'42', cache=cache)
        data = await gh.getitem("/fake")
        url = "https://api.github.com/fake"
        assert url in cache
        assert cache[url] == (None, last_modified, 42, None)
        assert data == cache[url][2]

    @pytest.mark.asyncio
    async def test_hit(self):
        url = "https://api.github.com/fake"
        cache = {url: ("12345", "67890", 42, None)}
        gh = MockGitHubAPI(304, cache=cache)
        data = await gh.getitem(url)
        assert data == 42

    @pytest.mark.asyncio
    async def test_miss(self):
        url = "https://api.github.com/fake"
        cache = {url: ("12345", "67890", 42, None)}
        headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
        headers["etag"] = "09876"
        headers["last-modified"] = "54321"
        gh = MockGitHubAPI(200, headers, body=b"-13", cache=cache)
        data = await gh.getitem(url)
        assert data == -13
        assert cache[url] == ("09876", "54321", -13, None)

    @pytest.mark.asyncio
    async def test_ineligible(self):
        cache = {}
        gh = MockGitHubAPI(cache=cache)
        url = "https://api.github.com/fake"
        # Only way to force a GET request with a body.
        await gh._make_request("GET", url, {}, 42, "asdf")
        assert url not in cache
        await gh.post(url, data=42)
        assert url not in cache

    @pytest.mark.asyncio
    async def test_redirect_without_cache(self):
        cache = {}
        gh = MockGitHubAPI(304, cache=cache)
        with pytest.raises(RedirectionException):
            await gh.getitem("/fake")

    @pytest.mark.asyncio
    async def test_no_cache(self):
        headers = MockGitHubAPI.DEFAULT_HEADERS.copy()
        headers["etag"] = "09876"
        headers["last-modified"] = "54321"
        gh = MockGitHubAPI(headers=headers)
        await gh.getitem("/fake")  # No exceptions raised.
