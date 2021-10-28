import string
from abc import ABC, abstractmethod
from shutil import get_terminal_size
from typing import List, Optional

from ..episodes import Episode
from ..exc import NoEpisodesFoundError, NoPodcastsFoundError
from ..podcasts import Podcast

from .filtering import Filter, get_filter_from_command_arguments


EPISODE_LISTING_TEMPLATE = (
    "[{episode_number}] {title}: {short_description_msg!r}{downloaded_msg}{tags_msg}"
)

PODCAST_LISTING_TEMPLATE = "{title}{episodes_msg}{tags_msg}"

VERBOSE_EPISODE_LISTING_TEMPLATE = (
    "[{episode_number}] {title}\n"
    "id: {id}\n"
    "{tags_msg}\n"
    "created at: {created_at}\n"
    "updated at: {updated_at}\n"
    "{downloaded_at_msg}"
    "{long_description}"
)

VERBOSE_PODCAST_LISTING_TEMPLATE = (
    "{title}\n"
    "{episodes_msg}\n"
    "{tags_msg}"
    "feed: {feed}\n"
    "created at: {created_at}\n"
    "updated at: {updated_at}"
)


class Lister(ABC):
    def __init__(self, filter: Filter):
        self._filter = filter

    @abstractmethod
    def list(self) -> str:
        pass


class EpisodeLister(Lister):
    def list(self, verbose: bool = False) -> str:
        podcasts = self._filter.podcasts

        num_podcasts = len(podcasts) - 1
        episodes_found = False
        for pod_idx, pod in enumerate(podcasts):
            episodes = self._filter.get_podcast_episodes(pod)
            if not episodes:
                continue

            episodes_found = True
            yield pod.title
            num_episodes = len(episodes) - 1
            for ep_idx, ep in enumerate(episodes):
                if verbose:
                    yield self._get_verbose_episode_listing(ep)
                    if ep_idx < num_episodes:
                        yield ""
                else:
                    yield self._get_episode_listing(ep)
            if pod_idx < num_podcasts:
                yield ""

        if not episodes_found:
            raise NoEpisodesFoundError()

    @staticmethod
    def _get_verbose_episode_listing(e: Episode) -> str:
        tags = ", ".join(e.tags)
        tags_msg = f"tags: {tags}"

        if e.downloaded_at:
            downloaded_at = e.downloaded_at.isoformat()
            downloaded_at_msg = f"downloaded at: {downloaded_at}\n"
        else:
            downloaded_at_msg = ""

        return VERBOSE_EPISODE_LISTING_TEMPLATE.format(
            episode_number=e.episode_number,
            title=e.title,
            id=e.id,
            tags_msg=tags_msg,
            created_at=e.created_at.isoformat(),
            updated_at=e.updated_at.isoformat(),
            downloaded_at_msg=downloaded_at_msg,
            long_description=e.long_description,
        )

    def _get_episode_listing(self, episode: Episode):
        if episode.downloaded_at:
            downloaded_msg = " [X]"
        else:
            downloaded_msg = ""
        if episode.tags:
            tags = ", ".join(episode.tags)
            tags_msg = f" -> {tags}"
        else:
            tags_msg = ""

        template_kwargs = {
            "episode_number": episode.episode_number,
            "title": episode.title,
            "downloaded_msg": downloaded_msg,
            "tags_msg": tags_msg,
        }
        template_kwargs["short_description_msg"] = self._get_short_description_msg(
            episode.short_description, **template_kwargs
        )

        return EPISODE_LISTING_TEMPLATE.format(**template_kwargs)

    @staticmethod
    def _get_short_description_msg(short_description: str, **template_kwargs) -> str:
        terminal_width = get_terminal_size().columns
        short_description_length = terminal_width - len(
            EPISODE_LISTING_TEMPLATE.format(short_description_msg="", **template_kwargs)
        )
        short_description_words = short_description.split()
        short_description_msg = short_description_words[0]
        for word in short_description_words[1:]:
            new_short_description_msg = short_description_msg + f" {word}"
            if len(new_short_description_msg) > short_description_length:
                break
            short_description_msg = new_short_description_msg
        return short_description_msg.rstrip(string.punctuation)


class PodcastLister(Lister):
    def list(self, verbose: bool = False) -> str:
        podcasts = self._filter.podcasts

        if not podcasts:
            raise NoPodcastsFoundError()

        num_podcasts = len(podcasts) - 1
        for idx, pod in enumerate(podcasts):
            if verbose:
                yield self._get_verbose_podcast_listing(pod)
                if idx < num_podcasts:
                    yield ""
            else:
                yield self._get_podcast_listing(pod)

    def _get_verbose_podcast_listing(self, podcast: Podcast) -> List[str]:
        episodes_msg = f"{podcast.number_of_new_episodes} new episodes"
        if podcast.tags:
            tags = ", ".join(podcast.tags)
            tags_msg = f"tags: {tags}\n"
        else:
            tags_msg = ""
        return VERBOSE_PODCAST_LISTING_TEMPLATE.format(
            title=podcast.title,
            episodes_msg=episodes_msg,
            tags_msg=tags_msg,
            feed=podcast.feed,
            created_at=podcast.created_at.isoformat(),
            updated_at=podcast.updated_at.isoformat(),
        )

    def _get_podcast_listing(self, podcast: Podcast) -> str:
        new_episodes = podcast.number_of_new_episodes
        if new_episodes:
            episodes_msg = f" [{new_episodes}]"
        else:
            episodes_msg = ""
        if podcast.tags:
            tags = ", ".join(podcast.tags)
            tags_msg = f" -> {tags}"
        else:
            tags_msg = ""
        return PODCAST_LISTING_TEMPLATE.format(
            title=podcast.title, episodes_msg=episodes_msg, tags_msg=tags_msg
        )


def get_lister_from_command_arguments(
    list_episodes: bool = False, podcast_title: Optional[str] = None, **kwargs
):
    filter = get_filter_from_command_arguments(
        list_episodes=list_episodes, podcast_title=podcast_title, **kwargs
    )

    list_episodes = list_episodes or podcast_title
    if list_episodes:
        lister_cls = EpisodeLister
    else:
        lister_cls = PodcastLister

    return lister_cls(filter=filter)
