"""Helpers for the `ls` Click command defined in `pod_store.__main__`."""

from typing import List

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store


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


def _get_podcast_episode_listing(e: Episode):
    if e.downloaded_at:
        downloaded_msg = "[X]"
    else:
        downloaded_msg = ""
    return f"[{e.episode_number}] {e.title} {downloaded_msg}"


def list_podcasts(podcasts: List[Podcast]) -> str:
    """Return a formatted string of podcast output for the `ls` command."""
    return "\n".join([_get_podcast_listing(p) for p in podcasts])


def _get_podcast_listing(p: Podcast):
    new_episodes = p.number_of_new_episodes
    if new_episodes:
        episodes_msg = f"[{new_episodes}]"
    else:
        episodes_msg = ""
    if p.tags:
        tags = ", ".join(p.tags)
        tags_msg = f" -> {tags}"
    else:
        tags_msg = ""
    return f"{p.title} {episodes_msg}{tags_msg}"
