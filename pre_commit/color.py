from __future__ import unicode_literals

import sys

RED = '\033[41m'
GREEN = '\033[42m'
YELLOW = '\033[43;30m'
TURQUOISE = '\033[46;30m'
NORMAL = '\033[0m'


class InvalidColorSetting(ValueError):
    pass


def format_color(text, color, use_color_setting):
    """Format text with color.

    Args:
        text - Text to be formatted with color if `use_color`
        color - The color start string
        use_color_setting - Whether or not to color
    """
    if not use_color_setting:
        return text
    else:
        return u'{0}{1}{2}'.format(color, text, NORMAL)


def use_color(setting):
    """Choose whether to use color based on the command argument.

    Args:
        setting - Either `auto`, `always`, or `never`
    """
    if setting not in ('auto', 'always', 'never'):
        raise InvalidColorSetting(setting)

    return (
        setting == 'always' or
        (setting == 'auto' and sys.stdout.isatty())
    )
