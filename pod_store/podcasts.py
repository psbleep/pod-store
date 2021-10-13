import os
import re
from datetime import datetime
from typing import Any, List, Optional, Type, TypeVar

import feedparser

from . import util
from .episodes import Episode
from .exc import EpisodeDoesNotExistError, NoEpisodesFoundError

P = TypeVar("P", bound="Podcast")


class PodcastEpisodes:
    """Class for tracking all the episodes associated with a
    `pod_store.podcasts.Podcast` object.

    _episodes_download_path (str): location in file system the podcast will download
        episodes to.

    _episodes (dict):
        {id: `pod_store.episodes.Episode`}
    """

    def __init__(self, episode_data: dict, episode_downloads_path: str):
        self._episode_downloads_path = episode_downloads_path

        self._episodes = {
            id: Episode.from_json(**episode) for id, episode in episode_data.items()
        }

    def add(
        self,
        id: str,
        episode_number: str,
        title: str,
        download_path: str = None,
        **kwargs,
    ) -> None:
        """Add a new episode.

        Will construct a download path if none is provided, using the
        `_episodes_download_path` property and the episode number and title passed in.
        """
        download_path = download_path or os.path.join(
            self._episode_downloads_path, f"{episode_number}-{title}.mp3"
        )
        episode = Episode(
            id=id,
            episode_number=episode_number,
            title=title,
            download_path=download_path,
            **kwargs,
        )
        self._episodes[id] = episode
        return episode

    def delete(self, id: str) -> None:
        """Delete an episode.

        Looks up by store ID.
        """
        try:
            del self._episodes[id]
        except KeyError:
            raise EpisodeDoesNotExistError(id)

    def get(self, id: str, allow_empty: bool = False) -> Episode:
        """Retrieve an episode.

        Looks up by store ID.

        When `allow_empty` is set to `True`, will return `None` if no episode is found.
        """
        episode = self._episodes.get(id)
        if not episode and not allow_empty:
            raise EpisodeDoesNotExistError(id)
        return episode

    def list(self, allow_empty: bool = True, **filters) -> List[Episode]:
        """Return a list of podcast episodes, sorted by time created
        (most recent first).

        When `allow_empty` is set to `False`, an exception is raised if no episodes
        are found.

        Optionally provide a list of keyword arguments to filter results by.

            list(foo="bar")

        will check for a `foo` attribute on the `pod_store.episodes.Episode` object and
        check if the value matches "bar".
        """
        episodes = self._episodes.values()
        for key, value in filters.items():
            episodes = [e for e in episodes if getattr(e, key) == value]
        if not episodes and not allow_empty:
            raise NoEpisodesFoundError()

        return sorted(episodes, key=lambda e: e.created_at, reverse=True)

    def to_json(self):
        """Provide json data for all of the podcast episodes."""
        return {id: episode.to_json() for id, episode in self._episodes.items()}


class Podcast:
    """Podcast tracked in the store.

    title (str): podcast title
    episode_downloads_path (str): location in file system to download podcast episodes
    feed (str): RSS feed URL

    episode_data (dict): data about podcast episodes loaded from the store json.
        is used to construct the `PodcastEpisodes` class.

    created_at (timestamp)
    updated_at (timestamp)

    episodes (PodcastEpisodes)
    """

    def __init__(
        self,
        title: str,
        episode_downloads_path: str,
        feed: str,
        episode_data: dict,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.title = title
        self.episode_downloads_path = episode_downloads_path
        self.feed = feed
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

        self.episodes = PodcastEpisodes(
            episode_data=episode_data, episode_downloads_path=episode_downloads_path
        )

    @classmethod
    def from_json(
        cls: Type[P], created_at: datetime, updated_at: datetime, **kwargs
    ) -> P:
        """Load a `pod_store.podcasts.Podcast` object from json data.

        Parses `datetime` objects from json strings where appropriate.
        """
        created_at = util.parse_datetime_from_json(created_at)
        updated_at = util.parse_datetime_from_json(updated_at)
        return cls(created_at=created_at, updated_at=updated_at, **kwargs)

    def __eq__(self, other: Any) -> bool:
        try:
            other_json = other.to_json()
        except AttributeError:
            return False
        return self.to_json() == other_json

    def __repr__(self) -> str:
        return f"Podcast({self.title!r})"

    def __str__(self) -> str:
        new_episodes = self.number_of_new_episodes
        if new_episodes:
            episodes_msg = f"[{new_episodes}]"
        else:
            episodes_msg = ""
        return f"{self.title} {episodes_msg}"

    @property
    def has_new_episodes(self) -> bool:
        """Inidicates if the podcast has any new episodes."""
        return bool(self.episodes.list(downloaded_at=None))

    @property
    def number_of_new_episodes(self) -> int:
        return len(self.episodes.list(downloaded_at=None))

    def refresh(self) -> None:
        """Refresh the episode data tracked in the pod store for this podcast.

        Parses the RSS feed and:

            - adds new episodes to the `PodcastEpisodes` listing if they are in the feed
              but not being tracked yet.
            - updates existing episodes in the `PodcastEpisodes` listing from data
              found in the feed.
            - removes episodes tracked in the `PodcastEpisodes` listing that are no
              longer present in the feed.
        """
        episodes_seen = []

        feed_data = feedparser.parse(self.feed)
        number_of_entries = len(feed_data.entries)
        for entry_number, raw_data in enumerate(feed_data.entries):
            episode_data = self._parse_episode_feed_data(**raw_data)

            # If no episode number can be parsed from the RSS feed data, guess based
            # on position in the loop.
            episode_number = episode_data.get("episode_number") or (
                str(number_of_entries - entry_number)
            )
            episode_data["episode_number"] = self._pad_episode_number(episode_number)

            episode = self.episodes.get(episode_data["id"], allow_empty=True)
            if episode:
                episode.update(**episode_data)
            else:
                self.episodes.add(**episode_data)

            episodes_seen.append(episode_data["id"])

        # clean up old episodes no longer present in the feed
        for episode in self.episodes.list():
            if episode.id not in episodes_seen:
                self.episodes.delete(episode.id)

    def to_json(self) -> dict:
        """Convert podcast data into a json-able dict.

        Parses datetime fields into isoformat strings for json storage.
        """
        created_at = util.parse_datetime_to_json(self.created_at)
        updated_at = util.parse_datetime_to_json(self.updated_at)
        return {
            "title": self.title,
            "episode_downloads_path": self.episode_downloads_path,
            "feed": self.feed,
            "created_at": created_at,
            "updated_at": updated_at,
            "episode_data": self.episodes.to_json(),
        }

    def _parse_episode_feed_data(
        self,
        id: str,
        title: str,
        links: list,
        published_parsed: tuple,
        updated_parsed: Optional[tuple] = None,
        itunes_episode: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Converts the raw RSS feed data into a dict of valid `pod.episode.Episode`
        attributes.

        - Parses an ID for use in the store from the RSS feed ID.

        - Gathers an episode number (if available).

        - Determines a download URL from the available links in the RSS feed data.

        - Converts the `published` and `updated` data from the RSS feed into `datetime`
          objects.
        """
        id = self._parse_store_episode_id(id)

        episode_number = itunes_episode or self._parse_episode_number_from_rss_title(
            title
        )

        updated_parsed = updated_parsed or published_parsed

        return {
            "id": self._parse_store_episode_id(id),
            "episode_number": episode_number,
            "title": title,
            "url": [
                u["href"] for u in links if u["type"] in ("audio/mpeg", "audio/mp3")
            ][0],
            "created_at": datetime(*published_parsed[:6]),
            "updated_at": datetime(*updated_parsed[:6]),
        }

    @staticmethod
    def _parse_store_episode_id(rss_id: str) -> str:
        """Parse a store episode ID from the ID present in the RSS feed.

        The RSS feed IDs are sometimes lengthy URLs. Chop off the end, hopefully
        it includes a unique enough identifier.
        """
        return rss_id.split("/")[-1]

    @staticmethod
    def _parse_episode_number_from_rss_title(rss_title: str) -> str:
        """Try to get an episode number from the episode title in the RSS feed.

        Sometimes episode titles start or end with an episode number.

        This may be a very bad idea.
        """
        stripped_title = re.sub(r"[^A-Za-z0-9 ]+", "", rss_title)
        title_tokens = stripped_title.split()
        start_token, end_token = title_tokens[0], title_tokens[-1]

        if start_token.isdigit():
            return start_token
        elif end_token.isdigit():
            return end_token

    @staticmethod
    def _pad_episode_number(episode_number: str):
        """Create an episode number padded with up to 3 zeros."""
        return episode_number.rjust(4, "0")
