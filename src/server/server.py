import asyncio
import sys

from config import config
from aiohttp import web
from gidgethub import routing, sansio
from rules import rule_checker
from parser import parser

router = routing.Router()


def hello(request):
    return web.Response(text='hello itsa me mario')


async def healthz(request):
    return web.Response(text='OK')


async def github_webhook_handler(request):
    body = await request.read()
    secret = config.github_webhook_secret
    event = sansio.Event.from_http(request.headers, body, secret=secret)

    if event.event == 'ping':
        return web.Response(status=200)

    # Give GitHub some time to reach internal consistency.
    await asyncio.sleep(1)
    await router.dispatch(event, request.app.gh_api)
    return web.Response(status=200)


@router.register('pull_request', action='opened')
@router.register('pull_request', action='synchronize')
async def opened_pr(event, gh_api, *args, **kwargs):
    pr = event.data['pull_request']
    repo = pr['base']['repo']['name']
    author = pr['user']['login']
    comments_url = pr['comments_url']

    diff_url = pr['_links']['self']['href']  # does not use the diff_url field
    rules_url = f'{config.github_uri}/api/v3/repos/{config.github_owner}/{repo}/contents/barrelman.yml'

    futures = [
        gh_api.getitem(diff_url, accept=sansio.accept_format(media='diff', json=False)),
        gh_api.getitem(rules_url, accept=sansio.accept_format(media='raw', json=True)),
    ]

    diff, rules = await asyncio.gather(*futures)
    diff = parser.parse_diff(diff)

    # if a barrelman.yml file has changed or been added in this PR, check if in valid format
    if 'barrelman.yml' in diff:
        ref = pr['head']['ref']
        new_rules = await gh_api.getitem(f'{rules_url}?ref={ref}', accept=sansio.accept_format(media='raw', json=True))
        parsed = parser.parse_barrel_rules(new_rules)
        if type(parsed) is str:
            await _create_warning_comment(gh_api, comments_url, parsed, ref)

    if rules is None:
        return

    parsed = parser.parse_barrel_rules(rules)
    if type(parsed) is str:
        # if barrelman.yml file on master branch is corrupted
        await _create_error_comment(gh_api, comments_url, parsed)
        return

    checker = rule_checker.RuleChecker(parsed)
    checker.check_rules(diff)

    # Author of PR cannot be added as a reviewer
    checker.users_to_notify.discard(author)
    if len(checker.triggered_regex_rules) == 0:
        return

    futures = [
        _add_code_reviewers(gh_api, repo, pr['number'], list(checker.users_to_notify),
                            list(checker.teams_to_notify)),
        _create_comment(gh_api, comments_url, checker.triggered_regex_rules)
    ]
    await asyncio.gather(*futures)


async def _add_code_reviewers(gh_api, repo, pr_number, users, teams):
    review_url = f'{config.github_uri}/api/v3/repos/{config.github_owner}/{repo}/pulls/{pr_number}/requested_reviewers'
    await gh_api.post(review_url, data={'reviewers': users, 'team_reviewers': teams})


async def _create_comment(gh_api, comments_url, regex_rules):
    message = '**Patterns matched for this PR**:\n'
    for rule in regex_rules:
        message += '- ' + str(rule) + '\n'
    await gh_api.post(comments_url, data={'body': message})


async def _create_error_comment(gh_api, comments_url, message):
    error_msg = '**Something\'s wrong with barrelman.yml file on master:**\n' + message
    await gh_api.post(comments_url, data={'body': error_msg})


async def _create_warning_comment(gh_api, comments_url, message, ref):
    warning_msg = f'**Something\'s wrong with barrelman.yml file on branch {ref}:**\n' + message
    await gh_api.post(comments_url, data={'body': warning_msg})


class BarrelmanApp:
    def __init__(self, gh_api):
        self.app = web.Application()
        self.app.gh_api = gh_api

    def register_routes(self):
        self.app.router.add_get('/', hello)
        self.app.router.add_post('/webhook', github_webhook_handler)
        self.app.router.add_get('/healthz', healthz)

    def run(self):
        web.run_app(self.app, host='127.0.0.1', port=8000)
