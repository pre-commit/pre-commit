from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

FILE = None
DIRECTORY = DIR = None


def add_argument_to(
    parser: ArgumentParser, *args: list[Any], **kwargs: dict[Any, Any],
) -> ArgumentParser:
    from argparse import Action

    Action.complete = None  # type: ignore
    return parser
