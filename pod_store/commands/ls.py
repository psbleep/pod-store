"""Helpers for the `ls` Click command defined in `pod_store.__main__`."""
import shutil
import string
from typing import List

from ..episodes import Episode
from ..podcasts import Podcast
from ..store import Store

SHORT_EPISODE_LISTING = (
    "[{episode_number}] {title}: {short_description_msg!r}{downloaded_msg}{tags_msg}"
)
SHORT_PODCAST_LISTING = "{title}{episodes_msg}{tags_msg}"

TERMINAL_WIDTH = shutil.get_terminal_size().columns

VERBOSE_EPISODE_LISTING = (
    "[{episode_number}] {title}\n"
    "id: {id}\n"
    "{tags_msg}\n"
    "created at: {created_at}\n"
    "updated at: {updated_at}\n"
    "{downloaded_at_msg}"
    "{long_description}"
)

VERBOSE_PODCAST_LISTING = (
    "{title}\n"
    "{episodes_msg}\n"
    "{tags_msg}"
    "feed: {feed}\n"
    "created at: {created_at}\n"
    "updated at: {updated_at}"
)


def list_episodes_by_podcast(
    podcasts: List[Podcast], store: Store, verbose: bool, **episode_filters
) -> str:
    """Return a formatted string of podcast episode output for the `ls` command.

    `verbose` flag will list more detailed episode information.
    """
    output = []
    for pod in podcasts:
        episodes = pod.episodes.list(allow_empty=True, **episode_filters)
        if episodes:
            output.append(pod.title)
            for e in episodes:
                output.extend(_get_podcast_episode_listing(e, verbose=verbose))
            if not verbose:
                output.append("")
    output = output[:-1]  # remove extra newline at end of output
    return "\n".join(output)


def _get_podcast_episode_listing(e: Episode, verbose: bool) -> List[str]:
    if verbose:
        return _get_verbose_podcast_episode_listing(e)
    else:
        return _get_short_podcast_episode_listing(e)


def _get_verbose_podcast_episode_listing(e: Episode) -> List[str]:
    tags = ", ".join(e.tags)
    tags_msg = f"tags: {tags}"

    if e.downloaded_at:
        downloaded_at = e.downloaded_at.isoformat()
        downloaded_at_msg = f"downloaded at: {downloaded_at}\n"
    else:
        downloaded_at_msg = ""

    return (
        VERBOSE_EPISODE_LISTING.format(
            episode_number=e.episode_number,
            title=e.title,
            id=e.id,
            tags_msg=tags_msg,
            created_at=e.created_at.isoformat(),
            updated_at=e.updated_at.isoformat(),
            downloaded_at_msg=downloaded_at_msg,
            long_description=e.long_description,
        ).splitlines()
        + [""]
    )


def _get_short_podcast_episode_listing(e: Episode) -> List[str]:
    if e.downloaded_at:
        downloaded_msg = " [X]"
    else:
        downloaded_msg = ""
    if e.tags:
        tags = ", ".join(e.tags)
        tags_msg = f" -> {tags}"
    else:
        tags_msg = ""

    template_kwargs = {
        "episode_number": e.episode_number,
        "title": e.title,
        "downloaded_msg": downloaded_msg,
        "tags_msg": tags_msg,
    }
    template_kwargs["short_description_msg"] = _get_episode_short_description_msg(
        e.short_description, **template_kwargs
    )
    return SHORT_EPISODE_LISTING.format(**template_kwargs).splitlines()


def _get_episode_short_description_msg(
    short_description: str, **template_kwargs
) -> str:
    short_description_length = TERMINAL_WIDTH - len(
        SHORT_EPISODE_LISTING.format(short_description_msg="", **template_kwargs)
    )
    short_description_words = short_description.split()
    short_description_msg = short_description_words[0]
    for word in short_description_words[1:]:
        new_short_description_msg = short_description_msg + f" {word}"
        if len(new_short_description_msg) > short_description_length:
            break
        short_description_msg = new_short_description_msg
    return short_description_msg.rstrip(string.punctuation)


def list_podcasts(podcasts: List[Podcast], verbose: bool) -> str:
    """Return a formatted string of podcast output for the `ls` command."""
    podcast_listings = []
    for pod in podcasts:
        podcast_listings.extend(_get_podcast_listing(pod, verbose=verbose))
    if verbose:
        podcast_listings = podcast_listings[:-1]
    return "\n".join(podcast_listings)


def _get_podcast_listing(p: Podcast, verbose: bool) -> List[str]:
    if verbose:
        return _get_verbose_podcast_listing(p)
    else:
        return _get_short_podcast_listing(p)


def _get_verbose_podcast_listing(p: Podcast) -> List[str]:
    episodes_msg = f"{p.number_of_new_episodes} new episodes"
    if p.tags:
        tags = ", ".join(p.tags)
        tags_msg = f"tags: {tags}\n"
    else:
        tags_msg = ""
    return (
        VERBOSE_PODCAST_LISTING.format(
            title=p.title,
            episodes_msg=episodes_msg,
            tags_msg=tags_msg,
            feed=p.feed,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        ).splitlines()
        + [""]
    )


def _get_short_podcast_listing(p: Podcast) -> List[str]:
    new_episodes = p.number_of_new_episodes
    if new_episodes:
        episodes_msg = f" [{new_episodes}]"
    else:
        episodes_msg = ""
    if p.tags:
        tags = ", ".join(p.tags)
        tags_msg = f" -> {tags}"
    else:
        tags_msg = ""
    return SHORT_PODCAST_LISTING.format(
        title=p.title, episodes_msg=episodes_msg, tags_msg=tags_msg
    ).splitlines()
