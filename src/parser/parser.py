import yaml

from rules import rule

check = ' Check [the docs](https://github.com/Nextdoor/barrelman) for help.'

"""
Diffs have 4 kinds of lines
context lines, which start with a single space,
insertion lines that show a line that has been inserted, which start with a +,
deletion lines, which start with a -, and
metadata lines which describe higher level things like which file this is talking about, what options were used to generate the diff, 
    whether the file changed its permissions, etc.
"""


# Remove context lines to reduce false positives
# Only look at insertion lines or metadata lines
def parse_diff(diff):
    lines = diff.splitlines(True)
    for i in range(len(lines) - 1, -1, -1):
        first_char = str(lines[i])[0]
        if first_char == ' ' or first_char == '-':
            del lines[i]
        # Remove the plus
        elif first_char == '+':
            lines[i] = str(lines[i])[1:]
    parsed_diff = ''.join(lines)
    return parsed_diff


def parse_barrel_rules(yml):
    error_msg = ''
    try:
        patterns = yaml.safe_load(yml)
    except yaml.YAMLError as exc:
        if hasattr(exc, 'problem_mark'):
            if exc.context != None:
                error_msg += ('parser says ' + str(exc.problem_mark) + '\n  ' +
                              str(exc.problem) + ' ' + str(exc.context) +
                              '\nPlease correct barrelman.yml.' + check)
            else:
                error_msg += ('parser says ' + str(exc.problem_mark) + '\n  ' +
                              str(exc.problem) + '\nPlease correct barrelman.yml.' + check)
        else:
            error_msg += ('Something went wrong while parsing barrelman.yml file.' + check)
        return error_msg

    pattern_rules = []
    # yaml can generate a valid python object with no exceptions but format is incorrect
    try:
        for pattern, watchers in patterns.items():
            pattern_rules.append(rule.BarrelmanPatternRule(pattern, watchers))
    except:
        error_msg = 'Parsing barrelman.yml worked but the format is incorrect.\n'
        error_msg += '\n' + check
        return error_msg
    return pattern_rules
