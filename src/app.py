import aiohttp
import asyncio
import cachetools
import server
import utils
import uvloop

from config import config
from gidgethub import aiohttp_auth as gh_aiohttp

cache = cachetools.LRUCache(maxsize=500)

def initialize(loop):
    config.parse(loop=loop)


def create_github_api():
    return gh_aiohttp.GitHubAPI('barrelman', cache=cache)


def run_pre_start_coroutines(loop, gh_api):
    pre_start_coroutines = [
        gh_api.check,
    ]
    loop.run_until_complete(
        utils.run_coroutines_and_wait(pre_start_coroutines))


def create_app(gh_api):
    app = server.BarrelmanApp(gh_api)
    app.register_routes()
    return app


def entrypoint(loop=None):
    if __name__ == '__main__':
        if loop is None:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            loop = asyncio.get_event_loop()
        initialize(loop)
        gh_api = create_github_api()
        run_pre_start_coroutines(loop, gh_api)
        app = create_app(gh_api)
        app.run()


entrypoint()
