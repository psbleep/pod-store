"""Helpers for the `untag` Click command defined in `pod_store.__main__`."""

import click

from ..episodes import Episode
from ..podcasts import Podcast

INTERACTIVE_MODE_HELP = """Untagging in interactive mode. Options are:

    y = yes (tag this episode)
    n = no (do not tag this episode)
    b = bulk (untag this and all following episodes)
    q = quit (stop untagging episodes and quit)
"""


def handle_episode_untagging(
    tag: str, interactive_mode: bool, podcast: Podcast, episode: Episode
) -> (bool, bool):
    """Helper method for the details of untagging an episode.

    If the `untag` command is being run in interactive mode, will prompt the user to
    decide whether to untag the episode.

    Returns tuple of bools: whether the episode was untagged, whether we are in
    interactive mode.
    """
    if interactive_mode:
        confirm, interactive_mode = _untag_episode_interactively(
            podcast=podcast, episode=episode
        )
    else:
        # if we are not in interactive mode, we are in bulk-assignment mode.
        # all untags are pre-confirmed.
        confirm = True

    if confirm:
        episode.untag(tag)

    return confirm, interactive_mode


def _untag_episode_interactively(podcast: Podcast, episode: Episode) -> (bool, bool):
    """Helper for prompting the user whether to untag an episode as downloaded.

    User can also choose to switch from interactive to bulk-assignment mode here.

    Returns tuple of bools: whether the episode was untagged, whether we are in
    interactive mode.
    """
    interactive = True

    result = click.prompt(
        f"{podcast.title}: [{episode.episode_number}] {episode.title}",
        type=click.Choice(["y", "n", "b", "q"], case_sensitive=False),
    )

    if result == "y":
        confirm = True
    elif result == "n":
        confirm = False
    elif result == "q":
        raise click.Abort()
    else:
        confirm = True
        interactive = False

    return confirm, interactive
