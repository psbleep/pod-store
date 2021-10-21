"""Helpers for the `tag-episodes` and `untag-episodes` Click commands defined in
`pod_store.__main__`.
"""
from typing import Tuple

import click

from ..episodes import Episode
from ..podcasts import Podcast

INTERACTIVE_MODE_HELP = """{action}ging in interactive mode. Options are:

    y = yes ({action} this episode)
    n = no (do not {action} this episode)
    b = bulk ({action} this and all following episodes)
    q = quit (stop {action}ging episodes and quit)
"""


def handle_episode_tagging(
    tag: str, action: str, interactive_mode: bool, podcast: Podcast, episode: Episode
) -> Tuple[bool]:
    """Helper method for the details of tagging or untagging an episode.

    `action` is a string indicating whether to tag or untag.

    If the command is being run in interactive mode, will prompt the user to
    decide whether to perform the action.

    Returns tuple of bools: whether the action was performed, whether we are (still) in
    interactive mode.
    """
    if interactive_mode:
        confirm, interactive_mode = _determine_interactive_mode_action(
            podcast=podcast, episode=episode
        )
    else:
        # If we are not in interactive mode, we are in bulk-assignment mode.
        # All actions are pre-confirmed.
        confirm = True

    if confirm:
        if action == "tag":
            episode.tag(tag)
        elif action == "untag":
            episode.untag(tag)

    return confirm, interactive_mode


def _determine_interactive_mode_action(
    podcast: Podcast, episode: Episode
) -> Tuple[bool]:
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
