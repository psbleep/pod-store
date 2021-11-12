"""Podcasts tracked in the pod store.

Podcast objects are created/managed using the `pod_store.store.StorePodcasts` class."""
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any, List, Optional, Type, TypeVar

import feedparser
import requests

from . import PODCAST_DOWNLOADS_PATH, PODCAST_REFRESH_TIMEOUT, util
from .episodes import Episode
from .exc import EpisodeDoesNotExistError

P = TypeVar("P", bound="Podcast")


class PodcastEpisodes:
    """Class for tracking all the episodes associated with a
    `pod_store.podcasts.Podcast` object.

    _podcast (pod_store.Podcasts.Podcast): podcast these episodes belong to

    _episodes (dict):
        {id: `pod_store.episodes.Episode`}
    """

    def __init__(self, podcast: P, episode_data: dict) -> None:
        self._podcast = podcast
        self._episodes = {
            id: Episode.from_json(podcast=podcast, **episode)
            for id, episode in episode_data.items()
        }

    @property
    def ids(self) -> List[str]:
        """All the IDs of tracked episodes."""
        return [episode.id for episode in self.list()]

    def add(
        self,
        id: str,
        episode_number: str,
        title: str,
        **kwargs,
    ) -> None:
        """Add a new episode to the store."""
        episode = Episode(
            podcast=self._podcast,
            id=id,
            episode_number=episode_number,
            title=title,
            tags=["new"],
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

    def list(self) -> List[Episode]:
        """Return a list of podcast episodes, sorted by time created
        (most recent first).
        """
        episodes = self._episodes.values()
        return sorted(episodes, key=lambda e: e.created_at, reverse=True)

    def to_json(self) -> dict:
        """Provide json data for all of the podcast episodes."""
        return {id: episode.to_json() for id, episode in self._episodes.items()}


class Podcast:
    """Podcast tracked in the store.

    title (str): podcast title
    feed (str): RSS feed URL
    tags (list): arbitrary text tags assigned to the podcast

    episode_data (dict): data about podcast episodes loaded from the store json.
        is used to construct the `PodcastEpisodes` class.

    created_at (timestamp)
    updated_at (timestamp)

    episodes (PodcastEpisodes)
    """

    def __init__(
        self,
        title: str,
        feed: str,
        episode_data: dict,
        tags: List[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        tags = tags or []

        self.title = title
        self.feed = feed
        self.tags = tags
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

        self.episodes = PodcastEpisodes(podcast=self, episode_data=episode_data)

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

    @property
    def episode_downloads_path(self) -> str:
        """Determine the download path for podcast episodes.

        Builds the file path from the `POD_STORE_PODCASTS_DOWNLOAD_PATH` env var
        configuration (defaults to /home/<username>/Podcasts) and the podcast title.
        """
        return os.path.join(PODCAST_DOWNLOADS_PATH, self.title)

    @property
    def has_new_episodes(self) -> bool:
        """Inidicates if the podcast has any new episodes."""
        for episode in self.episodes.list():
            if episode.is_new:
                return True
        return False

    @property
    def number_of_new_episodes(self) -> int:
        """Indicates the number of new episodes a podcast has."""
        return len([e for e in self.episodes.list() if e.is_new])

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

        resp = requests.get(self.feed, timeout=PODCAST_REFRESH_TIMEOUT)
        content = BytesIO(resp.content)
        feed_data = feedparser.parse(content)

        number_of_entries = len(feed_data.entries)
        for entry_number, raw_data in enumerate(feed_data.entries):
            episode_data = self._parse_episode_feed_data(**raw_data)

            # If no episode number can be parsed from the RSS feed data, guess based
            # on position in the loop.
            episode_data["episode_number"] = episode_data.get("episode_number") or (
                number_of_entries - entry_number
            )

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

    def tag(self, tag_name: str) -> None:
        """Apply a tag to the podcast."""
        self.tags.append(tag_name)

    def untag(self, tag_name: str) -> None:
        """Remove a tag from the podcast."""
        self.tags = [t for t in self.tags if t != tag_name]

    def to_json(self) -> dict:
        """Convert podcast data into a json-able dict.

        Parses datetime fields into isoformat strings for json storage.
        """
        created_at = util.parse_datetime_to_json(self.created_at)
        updated_at = util.parse_datetime_to_json(self.updated_at)
        return {
            "title": self.title,
            "feed": self.feed,
            "tags": self.tags,
            "created_at": created_at,
            "updated_at": updated_at,
            "episode_data": self.episodes.to_json(),
        }

    def _parse_episode_feed_data(
        self,
        title: str,
        id: str,
        summary: str,
        links: list,
        published_parsed: tuple,
        subtitle: Optional[str] = None,
        itunes_episode: Optional[str] = None,
        updated_parsed: Optional[tuple] = None,
        **kwargs,
    ) -> dict:
        """Converts the raw RSS feed data into a dict of valid `pod.episode.Episode`
        attributes.

        - Parses an ID for use in the store from the RSS feed ID.

        - Strips HTML/non-ASCII characters from episode descriptions.

        - Determines a download URL from the available links in the RSS feed data.

        - Converts the `published` and `updated` data from the RSS feed into `datetime`
          objects.

        - Gathers an episode number (if available).
        """
        id = self._parse_store_episode_id(id)
        long_description = self._strip_html_and_non_ascii_characters(summary)
        url = self._get_download_url(links)
        published_parsed = datetime(*published_parsed[:6])

        if itunes_episode:
            episode_number = int(itunes_episode)
        else:
            episode_number = None

        if subtitle:
            short_description = self._strip_html_and_non_ascii_characters(subtitle)
        else:
            short_description = long_description

        if updated_parsed:
            updated_parsed = datetime(*updated_parsed[:6])
        else:
            updated_parsed = published_parsed

        return {
            "title": title,
            "id": id,
            "long_description": long_description,
            "url": url,
            "created_at": published_parsed,
            "episode_number": episode_number,
            "short_description": short_description,
            "updated_at": updated_parsed,
        }

    @staticmethod
    def _parse_store_episode_id(rss_id: str) -> str:
        """Parse a store episode ID from the ID present in the RSS feed.

        The RSS feed IDs are sometimes lengthy URLs. Chop off the end, hopefully
        it includes a unique enough identifier.
        """
        return rss_id.split("/")[-1]

    @staticmethod
    def _strip_html_and_non_ascii_characters(text: str) -> str:
        """Strip HTML tags and non-ASCII characters from RSS feed data."""
        return re.sub("<[^<]+?>", "", text.encode("ascii", "ignore").decode("utf-8"))

    @staticmethod
    def _get_download_url(links: List[dict]) -> str:
        """Determines the download link for the episode audio from the RSS links data.

        Prefers ogg format, otherwise selects the first audio link available.
        """
        download_urls = []
        for audio_link in [al for al in links if al["type"].startswith("audio/")]:
            if audio_link["type"] == "audio/ogg":
                return audio_link["href"]
            download_urls.append(audio_link["href"])
        return download_urls[0]
