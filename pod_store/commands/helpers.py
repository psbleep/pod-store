from typing import Any, List, Optional

import click

from ..podcasts import Podcast
from ..store import Store


def abort_if_false(ctx: click.Context, _, value: Any):
    """Callback for aborting a Click command from within an argument or option."""
    if not value:
        ctx.abort()


def get_podcasts(
    store: Store,
    has_new_episodes: Optional[bool] = None,
    title: Optional[str] = None,
    allow_empty: bool = False,
) -> List[Podcast]:
    """Helper method for filtering a list of podcasts in the store from cli args.

    Builds the filters used by the `pod_store.Store.StorePodcasts.list` method.
    """
    podcast_filters = {}
    if has_new_episodes:
        podcast_filters["has_new_episodes"] = True
    if title:
        podcast_filters["title"] = title

    return store.podcasts.list(allow_empty=allow_empty, **podcast_filters)
