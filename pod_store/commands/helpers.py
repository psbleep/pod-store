"""General helpers for the Click commands defined in `pod_store.__main__`."""
from typing import Any, List, Optional

import click

from ..episodes import Episode
from ..exc import (
    EpisodeDoesNotExistError,
    GPGCommandError,
    NoEpisodesFoundError,
    NoPodcastsFoundError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    ShellCommandError,
    StoreExistsError,
)
from ..podcasts import Podcast
from ..store import Store

POD_STORE_EXCEPTIONS_AND_ERROR_MESSAGE_TEMPLATES = {
    EpisodeDoesNotExistError: "Episode not found: {}.",
    GPGCommandError: "Error encountered when running GPG commands: {}.",
    NoEpisodesFoundError: "No episodes found. {}",
    NoPodcastsFoundError: "No podcasts found. {}",
    PodcastDoesNotExistError: "Podcast not found: {}.",
    PodcastExistsError: "Podcast with title already exists: {}.",
    ShellCommandError: "Error running shell command: {}.",
    StoreExistsError: "Store already initialized: {}.",
}


def abort_if_false(ctx: click.Context, _, value: Any) -> None:
    """Callback for aborting a Click command from within an argument or option."""
    if not value:
        ctx.abort()


def display_pod_store_error_from_exception(exception: Exception):
    try:
        error_msg_template = POD_STORE_EXCEPTIONS_AND_ERROR_MESSAGE_TEMPLATES[
            exception.__class__
        ]
        click.secho(error_msg_template.format(str(exception)), fg="red")
        raise click.Abort()
    except KeyError:
        raise exception


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
        episodes.extend(pod.episodes.list(**episode_filters))
    if not episodes and not allow_empty:
        raise NoEpisodesFoundError()
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


def get_tag_filters(tags: List[str], is_tagged: bool) -> dict:
    """Helper method for building tag filters.

    `is_tagged` boolean determines whether to filter for presence of tag (True)
    or absence of tag (False).
    """
    if is_tagged:
        return {t: True for t in tags}
    else:
        return {t: False for t in tags}
