"""List information about podcasts or episodes tracked in the store."""
import string
from abc import ABC, abstractmethod
from shutil import get_terminal_size
from typing import List, Optional

from ..episodes import Episode
from ..exc import NoEpisodesFoundError
from ..podcasts import Podcast
from .filtering import Filter, get_filter_from_command_arguments

EPISODE_LISTING_TEMPLATE = (
    "[{episode_number}] {title}: {short_description_msg}{downloaded_msg}{tags_msg}"
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
    """Base class for the episode and podcast lister classes.

    Seeks to relegate the complexity of presenting data about store items into a
    single module so it is not bleeding all over `__main__`.

    _filter: an appropriate filter for the type of item you want to list.
        see the pod_store.commands.filtering module
    """

    def __init__(self, filter: Filter) -> None:
        self._filter = filter

    @abstractmethod
    def list(self) -> str:
        pass


class EpisodeLister(Lister):
    """List information about podcast episodes."""

    def list(self, verbose: bool = False) -> str:
        """List information about the episodes that match the filter.

        verbose: bool
            provide more detailed episode listing
        """
        # Usually empty episode groups would be caught in the `EpisodeFilter` when
        # the `episodes` property was referenced. Since episodes are listed by podcast,
        # we never directly reference the `episodes` property. As such we have to check
        # separately for cases where no episodes are found.
        episodes_found = False

        podcasts = self._filter.podcasts
        last_pod_idx = len(podcasts) - 1

        for pod_idx, pod in enumerate(podcasts):
            episodes = self._filter.get_podcast_episodes(pod)
            if not episodes:
                continue

            episodes_found = True
            yield pod.title
            last_ep_idx = len(episodes) - 1
            for ep_idx, ep in enumerate(episodes):
                if verbose:
                    yield self._get_verbose_episode_listing(ep)
                    if ep_idx < last_ep_idx:
                        yield ""
                else:
                    yield self._get_episode_listing(ep)
            if pod_idx < last_pod_idx:
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
            long_description=e.long_description or "(no description)",
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

        # The template kwargs have to be gathered for use in the description message
        # helper anyway. To avoid doing so twice I build a dict for them here.
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
        """Fit the episode description to the available size of the terminal.

        Finds the available space by seeing how much room is taken up by the episode
        listing WITHOUT the description.

        Fills in the remaining space with the maximum number of words possible, tries
        to avoid cutting off words.

        This would break if the first word was too big to fit.
        """
        if not short_description:
            return "(no description)"

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
        stripped_short_description_msg = short_description_msg.rstrip(
            string.punctuation
        )
        return f"{stripped_short_description_msg!r}"


class PodcastLister(Lister):
    """List information about podcasts."""

    def list(self, verbose: bool = False) -> str:
        """List information about the episodes that match the filter.

        verbose: bool
            provide more detailed podcast listing
        """
        podcasts = self._filter.podcasts

        last_pod_idx = len(podcasts) - 1
        for idx, pod in enumerate(podcasts):
            if verbose:
                yield self._get_verbose_podcast_listing(pod)
                if idx < last_pod_idx:
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
    list_untagged_items: bool = False,
    list_episodes: bool = False,
    podcast_title: Optional[str] = None,
    **kwargs,
):
    """Helper method for building a lister based on common CLI arguments.

    Builds the filter that will be used by the lister first.
    """
    filter = get_filter_from_command_arguments(
        filter_untagged_items=list_untagged_items,
        filter_episodes=list_episodes,
        podcast_title=podcast_title,
        **kwargs,
    )

    list_episodes = list_episodes or podcast_title
    if list_episodes:
        lister_cls = EpisodeLister
    else:
        lister_cls = PodcastLister

    return lister_cls(filter=filter)
