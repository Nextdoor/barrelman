"""Provide an abstract base class for easier requests."""
import abc
import json
from typing import Any, AsyncGenerator, Dict, Mapping, MutableMapping, Tuple
from typing import Optional as Opt

from . import sansio


# Value represents etag, last-modified, data, and next page.
CACHE_TYPE = MutableMapping[str, Tuple[Opt[str], Opt[str], Any, Opt[str]]]


class GitHubAPI(abc.ABC):

    """Provide an idiomatic API for making calls to GitHub's API."""

    def __init__(self, requester: str, *, oauth_token: Opt[str] = None,
                 cache: Opt[CACHE_TYPE] = None) -> None:
        self.requester = requester
        self.oauth_token = oauth_token
        self._cache = cache
        self.rate_limit: Opt[sansio.RateLimit] = None

    @abc.abstractmethod
    async def _request(self, method: str, url: str, headers: Mapping,
                       body: bytes = b'') -> Tuple[int, Mapping, bytes]:
        """Make an HTTP request."""

    @abc.abstractmethod
    async def sleep(self, seconds: float) -> None:
        """Sleep for the specified number of seconds."""

    async def _make_request(self, method: str, url: str, url_vars: Dict,
                            data: Any, accept: str) -> Tuple[bytes, Opt[str]]:
        """Construct and make an HTTP request."""
        filled_url = sansio.format_url(url, url_vars)
        request_headers = sansio.create_headers(self.requester, accept=accept,
                                                oauth_token=self.oauth_token)
        cached = cacheable = False
        # Can't use None as a "no body" sentinel as it's a legitimate JSON type.
        if data == b"":
            body = b""
            request_headers["content-length"] = "0"
            if method == "GET" and self._cache is not None:
                cacheable = True
                try:
                    etag, last_modified, data, more = self._cache[filled_url]
                    cached = True
                except KeyError:
                    pass
                else:
                    if etag is not None:
                        request_headers["if-none-match"] = etag
                    if last_modified is not None:
                        request_headers["if-modified-since"] = last_modified
        else:
            charset = "utf-8"
            body = json.dumps(data).encode(charset)
            request_headers['content-type'] = f"application/json; charset={charset}"
            request_headers['content-length'] = str(len(body))
        if self.rate_limit is not None and self.rate_limit.remaining is not None:
            self.rate_limit.remaining -= 1
        response = await self._request(method, filled_url, request_headers, body)
        if not (response[0] == 304 and cached):
            data, self.rate_limit, more = sansio.decipher_response(*response)
            has_cache_details = ("etag" in response[1]
                                 or "last-modified" in response[1])
            if self._cache is not None and cacheable and has_cache_details:
                etag = response[1].get("etag")
                last_modified = response[1].get("last-modified")
                self._cache[filled_url] = etag, last_modified, data, more
        return data, more

    async def getitem(self, url: str, url_vars: Dict = {},
                      *, accept: str = sansio.accept_format()) -> Any:
        """Send a GET request for a single item to the specified endpoint."""
        data, _ = await self._make_request("GET", url, url_vars, b"", accept)
        return data

    async def getiter(self, url: str, url_vars: Dict = {},
                      *, accept: str = sansio.accept_format()) -> AsyncGenerator[Any, None]:
        """Return an async iterable for all the items at a specified endpoint."""
        data, more = await self._make_request("GET", url, url_vars, b"", accept)
        for item in data:
            yield item
        if more:
            # `yield from` is not supported in coroutines.
            async for item in self.getiter(more, url_vars, accept=accept):
                yield item

    async def post(self, url: str, url_vars: Dict = {}, *, data: Any,
                   accept: str = sansio.accept_format()) -> Any:
        data, _ = await self._make_request("POST", url, url_vars, data, accept)
        return data

    async def patch(self, url: str, url_vars: Dict = {}, *, data: Any,
                    accept: str = sansio.accept_format()) -> Any:
        data, _ = await self._make_request("PATCH", url, url_vars, data, accept)
        return data

    async def put(self, url: str, url_vars: Dict = {}, *, data: Any = b"",
                  accept: str = sansio.accept_format()) -> Any:
        data, _ = await self._make_request("PUT", url, url_vars, data, accept)
        return data

    async def delete(self, url: str, url_vars: Dict = {}, *, data: Any = b"",
                     accept: str = sansio.accept_format()) -> None:
        await self._make_request("DELETE", url, url_vars, data, accept)
