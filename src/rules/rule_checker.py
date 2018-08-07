
class RuleChecker:
    def __init__(self, rules):
        self.rules = rules
        self.users_to_notify = set()
        self.teams_to_notify = set()
        self.triggered_regex_rules = []

    def check_rules(self, diff):
        for rule in self.rules:
            users, teams = rule.check_rule(diff)
            self.users_to_notify.update(users)
            self.teams_to_notify.update(teams)
            if users or teams:
                self.triggered_regex_rules.append(rule)
