"""Helpers for the `ls` Click command defined in `pod_store.__main__`."""
import shutil
import string
from typing import List

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store

TERMINAL_WIDTH = shutil.get_terminal_size().columns

SHORT_EPISODE_LISTING = (
    "[{episode_number}] {title}: {short_description_msg!r}{downloaded_msg}{tags_msg}"
)


def list_episodes_by_podcast(
    podcasts: List[Podcast], store: Store, verbose: bool, **episode_filters
) -> str:
    """Return a formatted string of podcast episode output for the `ls` command.

    `verbose` flag will list more detailed episode information.
    """
    output = []
    for pod in podcasts:
        episodes = pod.episodes.list(allow_empty=True, **episode_filters)
        if episodes:
            output.append(pod.title)
            output.extend(
                [_get_podcast_episode_listing(e, verbose=verbose) for e in episodes]
            )
            output.append("")
    output = output[:-1]  # remove extra newline at end of output
    return "\n".join(output)


def _get_podcast_episode_listing(e: Episode, verbose: bool) -> str:
    if verbose:
        return _get_verbose_podcast_episode_listing(e)
    else:
        return _get_short_podcast_episode_listing(e)


def _get_verbose_podcast_episode_listing(e: Episode):
    pass


def _get_short_podcast_episode_listing(e: Episode):
    if e.downloaded_at:
        downloaded_msg = " [X]"
    else:
        downloaded_msg = ""
    if e.tags:
        tags = ", ".join(e.tags)
        tags_msg = f" -> {tags}"
    else:
        tags_msg = ""

    template_kwargs = {
        "episode_number": e.episode_number,
        "title": e.title,
        "downloaded_msg": downloaded_msg,
        "tags_msg": tags_msg,
    }
    template_kwargs["short_description_msg"] = _get_episode_short_description_msg(
        e.short_description, **template_kwargs
    )
    return SHORT_EPISODE_LISTING.format(**template_kwargs)


def _get_episode_short_description_msg(short_description: str, **template_kwargs):
    short_description_length = TERMINAL_WIDTH - len(
        SHORT_EPISODE_LISTING.format(short_description_msg="", **template_kwargs)
    )
    short_description_words = short_description.split()
    short_description_msg = short_description_words[0]
    for word in short_description_words[1:]:
        new_short_description_msg = short_description_msg + f" {word}"
        if len(new_short_description_msg) > short_description_length:
            break
        short_description_msg = new_short_description_msg
    return short_description_msg.rstrip(string.punctuation)


def list_podcasts(podcasts: List[Podcast]) -> str:
    """Return a formatted string of podcast output for the `ls` command."""
    return "\n".join([_get_podcast_listing(p) for p in podcasts])


def _get_podcast_listing(p: Podcast) -> str:
    new_episodes = p.number_of_new_episodes
    if new_episodes:
        episodes_msg = f" [{new_episodes}]"
    else:
        episodes_msg = ""
    if p.tags:
        tags = ", ".join(p.tags)
        tags_msg = f" -> {tags}"
    else:
        tags_msg = ""
    return f"{p.title}{episodes_msg}{tags_msg}"
