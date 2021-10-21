"""Helpers for the `ls` Click command defined in `pod_store.__main__`."""
import shutil
from typing import List

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store

TERMINAL_WIDTH = shutil.get_terminal_size().columns

EPISODE_LISTING = (
    "[{episode_number}] {title}: {summary_msg!r}{downloaded_msg}{tags_msg}"
)


def list_episodes_by_podcast(
    podcasts: List[Podcast], store: Store, **episode_filters
) -> str:
    """Return a formatted string of podcast episode output for the `ls` command."""
    output = []
    for pod in podcasts:
        episodes = pod.episodes.list(allow_empty=True, **episode_filters)
        if episodes:
            output.append(pod.title)
            output.extend([_get_podcast_episode_listing(e) for e in episodes])
            output.append("")
    output = output[:-1]  # remove extra newline at end of output
    return "\n".join(output)


def _get_podcast_episode_listing(e: Episode) -> str:
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
    template_kwargs["summary_msg"] = _get_episode_summary_msg(
        e.summary, **template_kwargs
    )
    return EPISODE_LISTING.format(**template_kwargs)


def _get_episode_summary_msg(summary: str, **template_kwargs):
    summary_length = TERMINAL_WIDTH - len(
        EPISODE_LISTING.format(summary_msg="", **template_kwargs)
    )
    return summary[:summary_length]


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
