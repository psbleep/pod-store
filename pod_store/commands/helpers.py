import click
from typing import Any


def abort_if_false(ctx: click.Context, _, value: Any):
    """Callback for aborting a Click command from within an argument or option."""
    if not value:
        ctx.abort()
