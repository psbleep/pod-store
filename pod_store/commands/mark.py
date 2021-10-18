"""Helpers for the `mark` Click command defined in `pod_store.__main__`."""

import click

from ..episodes import Episode
from ..podcasts import Podcast

INTERACTIVE_MODE_HELP = """Marking in interactive mode. Options are:

    y = yes (mark as downloaded)
    n = no (do not mark as downloaded)
    b = bulk (mark this and all following episodes as 'downloaded')
    q = quit (stop marking episodes)
"""


def handle_episode_marking(
    interactive_mode: bool, podcast: Podcast, episode: Episode
) -> (bool, bool):
    """Helper method for the details of marking an episode.

    If the `mark` command is being run in interactive mode, will prompt the user to
    decide whether to mark the episode.

    Returns tuple of bools: whether the episode was marked, whether we are in
    interactive mode.
    """
    if interactive_mode:
        confirm, interactive_mode = _mark_episode_interactively(
            podcast=podcast, episode=episode
        )
    else:
        # if we are not in interactive mode, we are in bulk-assignment mode.
        # all marks are pre-confirmed.
        confirm = True

    if confirm:
        episode.mark_as_downloaded()

    return confirm, interactive_mode


def _mark_episode_interactively(podcast: Podcast, episode: Episode) -> (bool, bool):
    """Helper for prompting the user whether to mark an episode as downloaded.

    User can also choose to switch from interactive to bulk-assignment mode here.

    Returns tuple of bools: whether the episode was marked, whether we are in
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
