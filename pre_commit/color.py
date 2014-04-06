
import sys

RED = '\033[41m'
GREEN = '\033[42m'
NORMAL = '\033[0m'


def format_color(text, color, use_color):
    """Format text with color.

    Args:
        text - Text to be formatted with color if `use_color`
        color - The color start string
        use_color - Whether or not to color
    """
    if not use_color:
        return text
    else:
        return u'{0}{1}{2}'.format(color, text, NORMAL)


def use_color(setting):
    """Choose whether to use color based on the command argument.

    Args:
        setting - Either `auto`, `always`, or `never`
    """
    return (
        setting == 'always' or
        (setting == 'auto' and sys.stdout.isatty())
    )
