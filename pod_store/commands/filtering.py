"""Filter groups of podcasts or episodes."""
from abc import ABC, abstractproperty
from typing import Any, List, Optional, Union

from ..episodes import Episode
from ..exc import AmbiguousEpisodeError, NoEpisodesFoundError, NoPodcastsFoundError
from ..podcasts import Podcast
from ..store import Store


class Filter(ABC):
    """Base class for podcast and episode filter classes.

    _store: pod_store.Store

    new_episodes: bool
       Whether to filter based on new episodes. When used to filter episodes, results
       will be restricted to new episodes. When used to filter podcasts, only podcasts
       that have new episodes will be returned.

    podcast_title: str (optional)
       if provided, results will be restricted to podcasts with the title indicated,
       or to episodes that belong to the podcast with the title indicated.

    filters: dict (optional)
       other filter criteria

    podcast_filters: dict (optional)
       used in episode filtering to specify additional filters for which podcasts to
       include in the search.

    Since episodes are ultimately looked up from their podcasts, default podcast
    filtering behavior is defined here in the base class (since it will be needed in
    all filters).
    """

    def __init__(
        self,
        store: Store,
        new_episodes: bool = False,
        podcast_title: Optional[str] = None,
        podcast_filters: Optional[dict] = None,
        **filters,
    ) -> None:
        self.new_episodes = new_episodes
        self.podcast_title = podcast_title
        self.extra_podcast_filters = podcast_filters or {}
        self.filters = filters

        self._store = store

    @staticmethod
    def from_command_arguments(
        store: Store,
        new_episodes: bool = False,
        filter_for_episodes: bool = None,
        podcast_title: Optional[str] = None,
        episode_number: Optional[int] = None,
        tagged: Optional[List] = None,
        untagged: Optional[List] = None,
        podcasts_tagged: Optional[list] = None,
        podcasts_untagged: Optional[list] = None,
        **filters,
    ):
        tagged = tagged or []
        untagged = untagged or []
        podcasts_tagged = podcasts_tagged or []
        podcasts_untagged = podcasts_untagged or []

        if filter_for_episodes is None:
            filter_for_episodes = bool(podcast_title) or False

        if episode_number is not None:
            new_episodes = False
            if podcast_title is None:
                raise AmbiguousEpisodeError(episode_number)
            filters["episode_number"] = episode_number

        filters = {
            **{t: True for t in tagged},
            **{u: False for u in untagged},
            **filters,
        }

        podcast_filters = {
            **{pt: True for pt in podcasts_tagged},
            **{up: False for up in podcasts_untagged},
        }

        if filter_for_episodes:
            filter_cls = EpisodeFilter
        else:
            filter_cls = PodcastFilter

        return filter_cls(
            store=store,
            new_episodes=new_episodes,
            podcast_title=podcast_title,
            podcast_filters=podcast_filters,
            **filters,
        )

    @abstractproperty
    def items(self) -> List:
        pass

    @property
    def podcasts(self) -> List[Podcast]:
        """List of podcasts that meet the filter criteria."""
        podcasts = [
            p
            for p in self._store.podcasts.list()
            if self._passes_filters(p, **self._podcast_filters)
        ]
        if not podcasts:
            raise NoPodcastsFoundError()
        return podcasts

    @property
    def _podcast_filters(self) -> dict:
        """Builds the podcast filters dict.

        Adds filters based on the `_new_episodes` and `_podcast_title` attributes when
        appropriate.
        """
        filters = {}
        if self.new_episodes:
            filters["has_new_episodes"] = True
        if self.podcast_title:
            filters["title"] = self.podcast_title
        return {**filters, **self.extra_podcast_filters}

    def _passes_filters(self, obj: Union[Episode, Podcast], **filters) -> bool:
        """Checks whether a podcast/episode meets all the provided filter criteria."""
        for key, value in filters.items():
            if not self._check_filter_criteria(obj, key, value):
                return False
        return True

    @staticmethod
    def _check_filter_criteria(
        obj: Union[Episode, Podcast], key: str, value: Any
    ) -> bool:
        """Determines if an episode or podcast meets a filter criteria.

        Checks if the attribute `key` on the object `obj` matches the supplied `value`.

        If no attribute is found on `obj` to match `key`, attempts to check for tags.

           - if `value` is True: check for presence of a tag named `key`
           - if `value` is False: check for absence of a tag named `key`
        """
        try:
            return getattr(obj, key) == value
        except AttributeError as err:
            if value is True:
                return key in obj.tags
            elif value is False:
                return key not in obj.tags
            else:
                raise err


class EpisodeFilter(Filter):
    """Filter a group of episodes based on the provided criteria."""

    @property
    def items(self) -> List[Episode]:
        return self._episodes

    @property
    def _episode_filters(self) -> dict:
        """Builds the episode filters dict.

        Adds filters based on the `_new_episodes` attribute whee appropriate.
        """
        filters = self.filters
        if self.new_episodes:
            filters["new"] = True
        return filters

    @property
    def _episodes(self) -> List[Episode]:
        """List of episodes that meet the filter criteria."""
        episodes = []
        for pod in self.podcasts:
            episodes.extend(self.get_podcast_episodes(pod))
        if not episodes:
            raise NoEpisodesFoundError()
        return episodes

    def get_podcast_episodes(self, podcast: Podcast) -> List[Episode]:
        """List of episodes that meet the filter criteria for a particular podcast."""
        return [
            e
            for e in podcast.episodes.list()
            if self._passes_filters(e, **self._episode_filters)
        ]

    def __repr__(self) -> str:
        return "<EpisodeFilter>"


class PodcastFilter(Filter):
    """Filter a group of podcasts based on the provided criteria.

    Overrides some base class behavior: if we are filtering for a single podcast by
    title, ignore the `_new_episodes` attribute if it was set. Assume that the user
    wants to see the podcast indicated regardless of whether it has new episodes or not.
    """

    def __init__(self, podcast_title: Optional[str] = None, *args, **kwargs):
        super().__init__(podcast_title=podcast_title, *args, **kwargs)
        if podcast_title:
            self.new_episodes = False

    @property
    def _podcast_filters(self) -> dict:
        """Builds the podcast filters dict.

        Uses the podcast filters from the base class, and adds in the user-provided
        filters.
        """
        return {**self.filters, **super()._podcast_filters}

    @property
    def items(self) -> List[Podcast]:
        return self.podcasts

    def __repr__(self):
        return "<PodcastFilter>"
