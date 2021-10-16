"""Helpers for the `ls` Click command defined in `pod_store.__main__`."""

from typing import Optional

from .helpers import get_episodes
from ..store import Store


def list_podcast_episodes(store: Store, new: bool, podcast_title: str) -> Optional[str]:
    """Return a formatted string of podcast episodes output.

    If no episodes matching the criteria exist fro the podcast, returns `None`.
    """
    episodes = get_episodes(
        store=store, new=new, podcast_title=podcast_title, allow_empty=True
    )
    if not episodes:
        return

    episode_listing = "\n".join([str(e) for e in episodes])
    return f"{podcast_title}\n{episode_listing}\n"
