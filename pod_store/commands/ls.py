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
    return str(e)
