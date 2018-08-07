import asyncio
from typing import Any, Mapping, Tuple

import aiohttp
import datetime
import jwt

from . import abc as gh_abc
from config import config

# Custom version of gidgethub's aiohttp that will handle token refresh

class GitHubAPI(gh_abc.GitHubAPI):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.token = None
        self.token_expires_at = None
        super().__init__(*args, **kwargs)

    async def check(self):
        await self._refresh_token()

    async def _request(self, method: str, url: str, headers: Mapping,
                       body: bytes = b'') -> Tuple[int, Mapping, bytes]:
        now = datetime.datetime.utcnow()
        token_expired = self.token_expires_at is not None and (self.token_expires_at - now).total_seconds() < 60
        if self.token is None or token_expired:
            await self._refresh_token()

        headers['authorization'] = f'token {self.token}'
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers,
                                         data=body) as response:
                return response.status, response.headers, await response.read()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def _refresh_token(self):
        now = datetime.datetime.utcnow()
        encoded_jwt = jwt.encode({
            'iat': now,
            'exp': now + datetime.timedelta(minutes=1),
            'iss': config.github_app_id,
        }, config.github_app_private_key, algorithm='RS256')

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    url=f'{config.github_uri}/api/v3/installations/{config.github_app_installation_id}/access_tokens',
                    headers={
                        'Accept': self._accept_types(),
                        'Authorization': f'Bearer {encoded_jwt.decode()}',
                    }
            ) as response:
                data = await response.json()
                self.token = data['token']
                self.token_expires_at = datetime.datetime.strptime(data['expires_at'], '%Y-%m-%dT%H:%M:%SZ')

    def _accept_types(self):
        accept_types = [
            # Standard
            'application/vnd.github.v3+json',
            # Integrations - https://developer.github.com/changes/2016-09-14-Integrations-Early-Access/
            'application/vnd.github.machine-man-preview+json',
            # Nested teams - https://developer.github.com/changes/2017-08-30-preview-nested-teams/
            'application/vnd.github.hellcat-preview+json',
            # Team reviewers - https://developer.github.com/changes/2017-07-26-team-review-request-thor-preview/
            'application/vnd.github.thor-preview+json',
        ]
        return ','.join(accept_types)
