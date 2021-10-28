from abc import ABC
from typing import List, Optional

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store


class Filter(ABC):
    def __init__(
        self,
        store: Store,
        new_episodes: bool = False,
        podcast_title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        list_untagged_items: Optional[bool] = None,
    ):
        self._store = store
        self._new_episodes = new_episodes
        self._podcast_title = podcast_title
        self._tags = tags
        self._list_untagged_items = list_untagged_items

    @property
    def _tag_filters(self) -> dict:
        if self._tags:
            if self._list_untagged_items:
                return {tag: False for tag in self._tags}
            else:
                return {tag: True for tag in self._tags}
        else:
            return {}

    @property
    def _podcast_filters(self) -> dict:
        filters = {}
        if self._new_episodes:
            filters["has_new_episodes"] = True
        if self._podcast_title:
            filters["title"] = self._podcast_title
        return filters

    @property
    def podcasts(self) -> List[Podcast]:
        return self._store.podcasts.list(**self._podcast_filters)


class EpisodeFilter(Filter):
    @property
    def _episode_filters(self):
        filters = self._tag_filters
        if self._new_episodes:
            filters["new"] = True
        return filters

    @property
    def episodes(self) -> List[Episode]:
        episodes = []
        for pod in self.podcasts:
            episodes.extend(self._get_podcast_episodes(pod))
        return episodes

    def _get_podcast_episodes(self, podcast: Podcast):
        return podcast.episodes.list(allow_empty=True, **self._episode_filters)


class PodcastFilter(Filter):
    def __init__(self, podcast_title: Optional[str] = None, *args, **kwargs):
        super().__init__(podcast_title=podcast_title, *args, **kwargs)
        if podcast_title:
            self._new_episodes = False

    @property
    def _podcast_filters(self):
        return {**self._tag_filters, **super()._podcast_filters}


def get_filter_from_command_arguments(
    store: Store,
    new_episodes: bool = False,
    list_episodes: bool = False,
    podcast_title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    list_untagged_items: bool = None,
):
    list_episodes = list_episodes or podcast_title
    if list_episodes:
        filter_cls = EpisodeFilter
    else:
        filter_cls = PodcastFilter

    return filter_cls(
        store=store,
        new_episodes=new_episodes,
        podcast_title=podcast_title,
        tags=tags,
        list_untagged_items=list_untagged_items,
    )
