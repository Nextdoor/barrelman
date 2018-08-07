import re

from config import config


class BarrelmanPatternRule:
    def __init__(self, pattern, watchers):
        self.pattern = pattern
        self.users, self.teams = [], []
        for watcher in watchers:
            if watcher.startswith('team/'):
                self.teams.append(watcher[5:])
            else:
                self.users.append(watcher)

    def check_rule(self, diff):
        matches = re.findall(self.pattern, diff)
        if len(matches) > 0:
            return self.users, self.teams
        return [], []

    def __str__(self):
        tagged_users = [user for user in self.users]
        tagged_teams = [f'@{config.github_owner}/' + team for team in self.teams]
        watchers_str = ', '.join(tagged_users + tagged_teams)
        return f'\'{self.pattern}\': {watchers_str}'
