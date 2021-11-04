"""General helpers for the Click commands defined in `pod_store.__main__`."""
from typing import Any

import click

from ..exc import (
    EpisodeDoesNotExistError,
    GPGCommandError,
    NoEpisodesFoundError,
    NoPodcastsFoundError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    ShellCommandError,
    StoreDoesNotExistError,
    StoreExistsError,
)

POD_STORE_EXCEPTIONS_AND_ERROR_MESSAGE_TEMPLATES = {
    EpisodeDoesNotExistError: "Episode not found: {}.",
    GPGCommandError: "Error encountered when running GPG commands: {}.",
    NoEpisodesFoundError: "No episodes found. {}",
    NoPodcastsFoundError: "No podcasts found. {}",
    PodcastDoesNotExistError: "Podcast not found: {}.",
    PodcastExistsError: "Podcast with title already exists: {}.",
    ShellCommandError: "Error running shell command: {}.",
    StoreDoesNotExistError: (
        "Store has not been set up. See the `init` command for set up instructions."
    ),
    StoreExistsError: "Store already initialized: {}.",
}


def abort_if_false(ctx: click.Context, _, value: Any) -> None:
    """Callback for aborting a Click command from within an argument or option."""
    if not value:
        ctx.abort()


def display_pod_store_error_from_exception(exception: Exception):
    """Match a custom `pod_store` exception to a more friendly error message
    that is displayed to the user.

    Aborts the Click command process.

    If the exception provided is not found in the custom error -> error message
    mapping, the exceptin is raised normally.
    """
    try:
        error_msg_template = POD_STORE_EXCEPTIONS_AND_ERROR_MESSAGE_TEMPLATES[
            exception.__class__
        ]
        click.secho(error_msg_template.format(str(exception)), fg="red")
        raise click.Abort()
    except KeyError:
        raise exception
