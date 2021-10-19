"""General helpers for the Click commands defined in `pod_store.__main__`."""
from typing import Any, List, Optional

import click

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store


def abort_if_false(ctx: click.Context, _, value: Any):
    """Callback for aborting a Click command from within an argument or option."""
    if not value:
        ctx.abort()


def get_episodes(
    store: Store,
    new: Optional[bool] = None,
    podcast_title: Optional[str] = None,
    allow_empty: bool = False,
    **episode_filters,
) -> List[Episode]:
    """Helper method for filtering a list of episodes in the store from cli args.

    Builds the filters used by the `pod_store.Podcasts.PodcastEpisodes.list` method.

    If no podcast title is specified, will look through episodes for all store podcasts.
    """
    podcast_filters = {}
    if podcast_title:
        podcast_filters["title"] = podcast_title
    if new:
        podcast_filters["has_new_episodes"] = True

    if new:
        episode_filters["new"] = True

    podcasts = store.podcasts.list(allow_empty=allow_empty, **podcast_filters)
    episodes = []
    for pod in podcasts:
        episodes.extend(pod.episodes.list(allow_empty=allow_empty, **episode_filters))
    return episodes


def get_podcasts(
    store: Store,
    has_new_episodes: Optional[bool] = None,
    title: Optional[str] = None,
    allow_empty: bool = False,
    **podcast_filters,
) -> List[Podcast]:
    """Helper method for filtering a list of podcasts in the store from cli args.

    Builds the filters used by the `pod_store.Store.StorePodcasts.list` method.
    """
    if has_new_episodes:
        podcast_filters["has_new_episodes"] = True
    if title:
        podcast_filters["title"] = title

    return store.podcasts.list(allow_empty=allow_empty, **podcast_filters)
