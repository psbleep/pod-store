"""List information about podcasts or episodes tracked in the store."""
import string
from shutil import get_terminal_size
from typing import Callable, List, Optional

from ..episodes import Episode
from ..exc import NoEpisodesFoundError
from ..podcasts import Podcast
from .filtering import EpisodeFilter, Filter

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


def episodes_presenter(pod_store_filter: Filter, verbose: bool = False) -> str:
    """List information about the episodes that match the pod_store_filter.

    verbose: bool
        provide more detailed episode listing
    """
    # Usually empty episode groups would be caught in the `EpisodeFilter` when
    # the `episodes` property was referenced. Since episodes are listed by podcast,
    # we never directly reference that `episodes` property. As such we have to check
    # separately for cases where no episodes are found.
    episodes_found = False

    podcasts = pod_store_filter.podcasts
    last_pod_idx = len(podcasts) - 1

    for pod_idx, pod in enumerate(podcasts):
        episodes = pod_store_filter.get_podcast_episodes(pod)
        if not episodes:
            continue

        episodes_found = True

        # List the podcast title first.
        yield pod.title

        last_ep_idx = len(episodes) - 1
        for ep_idx, ep in enumerate(episodes):
            if verbose:
                yield _get_verbose_episode_listing(ep)
                # An extra space is needed unless this is the last episode for the
                # podcast.
                if ep_idx < last_ep_idx:
                    yield ""
            else:
                yield _get_episode_listing(ep)
        if pod_idx < last_pod_idx:
            # An extra space is needed unless this is the last podcast.
            yield ""

    if not episodes_found:
        raise NoEpisodesFoundError()


def _get_verbose_episode_listing(e: Episode) -> str:
    tags = ", ".join(e.tags)
    tags_msg = f"tags: {tags}"

    if e.downloaded_at:
        downloaded_at = e.downloaded_at.isoformat()
        downloaded_at_msg = f"downloaded at: {downloaded_at}\n"
    else:
        downloaded_at_msg = ""

    return VERBOSE_EPISODE_LISTING_TEMPLATE.format(
        episode_number=e.padded_episode_number,
        title=e.title,
        id=e.id,
        tags_msg=tags_msg,
        created_at=e.created_at.isoformat(),
        updated_at=e.updated_at.isoformat(),
        downloaded_at_msg=downloaded_at_msg,
        long_description=e.long_description or "(no description)",
    )


def _get_episode_listing(episode: Episode):
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
        "episode_number": episode.padded_episode_number,
        "title": episode.title,
        "downloaded_msg": downloaded_msg,
        "tags_msg": tags_msg,
    }
    template_kwargs["short_description_msg"] = _get_short_description_msg(
        episode.short_description, **template_kwargs
    )

    return EPISODE_LISTING_TEMPLATE.format(**template_kwargs)


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
    stripped_short_description_msg = short_description_msg.rstrip(string.punctuation)
    return f"{stripped_short_description_msg!r}"


def podcasts_presenter(pod_store_filter: Filter, verbose: bool = False) -> str:
    """List information about the podcasts that match the pod_store_filter.

    verbose: bool
        provide more detailed podcast listing
    """
    podcasts = pod_store_filter.podcasts

    last_pod_idx = len(podcasts) - 1
    for idx, pod in enumerate(podcasts):
        if verbose:
            yield _get_verbose_podcast_listing(pod)
            if idx < last_pod_idx:
                yield ""
        else:
            yield _get_podcast_listing(pod)


def _get_verbose_podcast_listing(podcast: Podcast) -> List[str]:
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


def _get_podcast_listing(podcast: Podcast) -> str:
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


class Lister:
    """Coordinates listing data about items in the store.

    Seeks to relegate the complexity of presenting data about store items into a
    single module so it is not bleeding all over `__main__`.

    filter (Filter): an appropriate filter for the type of item you want to list.
        see the pod_store.commands.filtering module

    presenter (callable): handles the logic about presenting output to the user.
        see the `episodes_presenter` and `podcasts_presenter` functions in this module.
    """

    def __init__(self, pod_store_filter: Filter, presenter: Callable) -> None:
        self.presenter = presenter
        self._pod_store_filter = pod_store_filter

    @classmethod
    def from_command_arguments(
        cls,
        list_episodes: Optional[bool] = None,
        **filter_kwargs,
    ):
        """Constructs an appropriate `Lister` objects from arguments passed in to a
        command in the CLI.

        Builds an appropriate `Filter` object and selects the appropriate `presenter`.
        """
        pod_store_filter = Filter.from_command_arguments(
            filter_for_episodes=list_episodes,
            **filter_kwargs,
        )

        if isinstance(pod_store_filter, EpisodeFilter):
            return cls(pod_store_filter=pod_store_filter, presenter=episodes_presenter)
        else:
            return cls(pod_store_filter=pod_store_filter, presenter=podcasts_presenter)

    def list_items(self, verbose: bool = False) -> str:
        """List info about the filter's items.

        If the `verbose` flag is set, more info will be shown.
        """
        for msg in self.presenter(self._pod_store_filter, verbose=verbose):
            yield msg

    def __repr__(self) -> str:
        return "<Lister>"
