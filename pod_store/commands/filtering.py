"""Filter groups of podcasts or episodes."""
from abc import ABC
from typing import List, Optional, Union

from ..episodes import Episode
from ..exc import NoEpisodesFoundError, NoPodcastsFoundError
from ..podcasts import Podcast
from ..store import Store


class Filter(ABC):
    """Base class for podcast and episode filter classes.

    _store: pod_store.Store
    _new_episodes: bool
        Whether to filter based on new episodes. When used to filter episodes, results
        will be restricted to new episodes. When used to filter podcasts, only podcasts
        that have new episodes will be returned.
    _podcast_title: str (optional)
        if provided, results will be restricted to podcasts with the title indicated,
        or to episodes that belong to the podcast with the title indicated.
    _tags: list [str] (optional)
        filter results by tags
    _filter_untagged_items: bool (optional)
        if filtering by tags, indicates that we should look for items WITHOUT the tag(s)
        when this is not set, filtering by tag will return results WITH the tag(s).

    Since episodes are ultimately looked up from their podcasts, podcast filtering
    behavior is defined here in the base class (since it will be needed in all filters).
    """

    def __init__(
        self,
        store: Store,
        new_episodes: bool = False,
        podcast_title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        filter_untagged_items: Optional[bool] = None,
    ) -> None:
        self._store = store
        self._new_episodes = new_episodes
        self._podcast_title = podcast_title
        self._tags = tags
        self._filter_untagged_items = filter_untagged_items

    @property
    def _tag_filters(self) -> dict:
        """Build a tag filters dict.

        Determines whether to search for presence or absence of tags using the
        `_filter_untagged_items` attribute.
        """
        if self._tags:
            if self._filter_untagged_items:
                return {tag: False for tag in self._tags}
            else:
                return {tag: True for tag in self._tags}
        else:
            return {}

    @property
    def _podcast_filters(self) -> dict:
        """Builds the podcast filters dict.

        Adds filters based on the `_new_episodes` and `_podcast_title` attributes when
        appropriate.
        """
        filters = {}
        if self._new_episodes:
            filters["has_new_episodes"] = True
        if self._podcast_title:
            filters["title"] = self._podcast_title
        return filters

    @property
    def podcasts(self) -> List[Podcast]:
        """List of podcasts that meet the filter criteria."""
        podcasts = self._store.podcasts.list(**self._podcast_filters)
        if not podcasts:
            raise NoPodcastsFoundError()
        return podcasts


class EpisodeFilter(Filter):
    """Filter a group of episodes based on the provided criteria."""

    @property
    def _episode_filters(self):
        """Builds the episode filters dict.

        Adds filters based on the `_new_episodes` attribute whee appropriate.
        """
        filters = self._tag_filters
        if self._new_episodes:
            filters["new"] = True
        return filters

    @property
    def episodes(self) -> List[Episode]:
        """List of episodes that meet the filter criteria."""
        episodes = []
        for pod in self.podcasts:
            episodes.extend(self.get_podcast_episodes(pod))
        if not episodes:
            raise NoEpisodesFoundError()
        return episodes

    def get_podcast_episodes(self, podcast: Podcast) -> List[Episode]:
        """List of episodes that meet the filter criteria for a particular podcast."""
        return podcast.episodes.list(allow_empty=True, **self._episode_filters)


class PodcastFilter(Filter):
    """Filter a group of podcasts based on the provided criteria.

    Overrides some base class behavior: if we are filtering for a single podcast by
    title, ignore the `_new_episodes` attribute if it was set. Assume that the user
    wants to see the podcast indicated regardless of whether it has new episodes or not.
    """

    def __init__(self, podcast_title: Optional[str] = None, *args, **kwargs):
        super().__init__(podcast_title=podcast_title, *args, **kwargs)
        if podcast_title:
            self._new_episodes = False

    @property
    def _podcast_filters(self):
        """Builds the podcast filters dict.

        Uses the podcast filters from the base class, and adds in the tag filters.
        """
        return {**self._tag_filters, **super()._podcast_filters}


def get_filter_from_command_arguments(
    store: Store,
    new_episodes: bool = False,
    filter_episodes: bool = False,
    podcast_title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    filter_untagged_items: bool = None,
) -> Union[EpisodeFilter, PodcastFilter]:
    """Helper method for building a filter based on common CLI command arguments."""
    filter_episodes = filter_episodes or podcast_title
    if filter_episodes:
        filter_cls = EpisodeFilter
    else:
        filter_cls = PodcastFilter

    return filter_cls(
        store=store,
        new_episodes=new_episodes,
        podcast_title=podcast_title,
        tags=tags,
        filter_untagged_items=filter_untagged_items,
    )
