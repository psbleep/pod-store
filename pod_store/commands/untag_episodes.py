"""Helpers for the `tag-episodes` and `untag-episodes` Click commands defined in
`pod_store.__main__`.
"""
from typing import Tuple

import click

from ..episodes import Episode
from ..podcasts import Podcast
from .taggers import PodcastEpisodeTagger

INTERACTIVE_MODE_HELP = """Tagging in interactive mode. Options are:

    y = yes (tag this episode)
    n = no (do not tag this episode)
    b = bulk (tag this and all following episodes)
    q = quit (stop tagging episodes and quit)
"""


TAG_EPISODES_COMMIT_MESSAGE = (
    "{action} {target} podcast episodes -> {tag}, {mode} mode."
)


def tag_episodes_commit_message_builder(ctx_params: dict, action: str) -> str:
    """Builds a `git` commit message for tagging/untagging a group of episodes.

    Specifies which episodes were tagged/untagged and the tag used.

    Pass in the `action` string to indicate whether episodes are being tagged or
    untagged.
    """
    action = action.capitalize()

    podcast_title = ctx_params.get("podcast")
    if podcast_title:
        target = f"{podcast_title!r}"
    else:
        target = "all"

    episode_id = ctx_params.get("episode")
    if episode_id:
        target = f"{target}, episode {episode_id!r}"

    tag = ctx_params.get("tag")

    if ctx_params.get("interactive"):
        mode = "interactive"
    else:
        mode = "bulk"

    return TAG_EPISODES_COMMIT_MESSAGE.format(
        action=action, target=target, tag=tag, mode=mode
    )


def get_podcast_episode_tagger(tag: str, podcasts: list, interactive_mode: bool):
    tagged_message_template = (
        "Tagged as {tag!r}: "
        "{episode.podcast.title} -> [{episode.episode_number}] {episode.title}"
    )

    prompt_message_template = (
        "{episode.podcast.title}: [{episode.episode_number}] {episode.title}"
    )
    return PodcastEpisodeTagger(
        tag=tag,
        podcasts=podcasts,
        tagged_message_template=tagged_message_template,
        interactive_mode=interactive_mode,
        interactive_mode_help_message=INTERACTIVE_MODE_HELP,
        interactive_mode_prompt_message_template=prompt_message_template,
    )


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
