import json
import os
import re
from datetime import datetime
from typing import Any, List, Optional, Type, TypeVar

import feedparser

from . import (
    DOWNLOADS_PATH,
    STORE_EPISODE_FILE_EXTENSION,
    STORE_PODCAST_FILE_EXTENSION,
    util,
)
from .episode import Episode
from .exc import PodcastDoesNotExistError

P = TypeVar("P", bound="Podcast")


class Podcast:
    """Podcast tracked in the pod store.

    _downloads_path: Location in the file system for episodes to be downloaded to.
    _store_file_path: file path for the episode file in the pod store

    title: podcast title
    feed: RSS feed URL
    created_at: timestamp
    updated_at: timestamp

    store_episodes_path: Location in the pod store where episode files are tracked.
    """

    def __init__(
        self,
        store_file_path: str,
        title: str,
        feed: str,
        created_at: datetime,
        updated_at: datetime,
    ):
        self._store_file_path = store_file_path

        self._downloads_path = os.path.join(DOWNLOADS_PATH, title)

        self.title = title
        self.feed = feed
        self.created_at = created_at
        self.updated_at = updated_at

        parent = os.path.dirname(self._store_file_path)
        dir_name = self._store_file_path[: -len(STORE_PODCAST_FILE_EXTENSION)]
        self.store_episodes_path = os.path.join(parent, dir_name)

    def __eq__(self, other: Any) -> bool:
        try:
            other_json = other.to_json()
        except AttributeError:
            return False
        return self.to_json() == other_json

    def __repr__(self) -> str:
        return f"Podcast({self.to_json()})"

    @classmethod
    def from_store_file(cls: Type[P], store_file_path: str) -> P:
        """Instantiates a `Podcast` object from the contents of a file tracked in the
        store.

        The store tracks podcast data in a json file containing a dict with the keys:
        `title`, `feed`, `created_at`, `updated_at`

        Datetime information is parsed from the json file into `datetime` objects.
        """
        try:
            with open(store_file_path) as f:
                podcast_data = json.load(f)
        except FileNotFoundError:
            raise PodcastDoesNotExistError(store_file_path)

        created_at = util.parse_datetime_from_json(podcast_data.pop("created_at"))
        updated_at = util.parse_datetime_from_json(podcast_data.pop("updated_at"))
        return cls(
            store_file_path=store_file_path,
            created_at=created_at,
            updated_at=updated_at,
            **podcast_data,
        )

    @property
    def has_new_episodes(self) -> bool:
        """Inidicates if the podcast has any new episodes."""
        return bool(self.list_new_episodes())

    def list_episodes(self) -> List[Episode]:
        """List all episodes tracked in the pod store associated with this pocast.

        Ordered by most recently updated.
        """
        return sorted(
            list(self._gather_episodes()),
            key=lambda e: e.updated_at,
            reverse=True,
        )

    def list_new_episodes(self) -> List[Episode]:
        """List only new episodes tracked in the pod store for this podcast."""
        return list(filter(lambda e: e.downloaded_at is None, self.list_episodes()))

    def search_episodes(self, term: str) -> List[Episode]:
        """Search the pod store for episodes for this podcast with the search term in
        the title."""
        return [e for e in self.list_episodes() if term in e.title]

    def refresh(self) -> None:
        """Refresh the episode data tracked in the pod store for this podcast.

        Parses the RSS feed and:

            - adds new episodes to the store that are in the feed but not being tracked
            yet
            - updates existing episodes in the store from the data in the feed
            - removes episodes tracked in the store that are no longer present
            in the RSS feed
        """
        os.makedirs(self.store_episodes_path, exist_ok=True)
        store_file_paths_seen = []

        feed_data = feedparser.parse(self.feed)
        number_of_entries = len(feed_data.entries)
        for entry_number, raw_data in enumerate(feed_data.entries):
            listing_number = number_of_entries - entry_number
            episode_data = self._parse_episode_feed_data(
                listing_number=listing_number, **raw_data
            )

            store_id = episode_data["id"]
            store_file_path = self._get_episode_store_file_path_from_id(store_id)
            if os.path.exists(store_file_path):
                episode = Episode.from_store_file(
                    store_file_path=store_file_path,
                    base_download_path=self._downloads_path,
                )
                episode.update(**episode_data)
            else:
                episode = Episode(
                    store_file_path=store_file_path,
                    base_download_path=self._downloads_path,
                    **episode_data,
                )
            episode.save()
            store_file_paths_seen.append(store_file_path)

        # clean up old episodes no longer present in the feed
        for file_name in os.listdir(self.store_episodes_path):
            store_file_path = os.path.join(self.store_episodes_path, file_name)
            if store_file_path not in store_file_paths_seen:
                os.remove(store_file_path)

    def save(self) -> None:
        """Save podcast data to a json file in the pod store."""
        with open(self._store_file_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    def to_json(self) -> dict:
        """Convert podcast data into a json-able dict.

        Parses datetime fields into isoformat strings for json storage.
        """
        created_at = util.parse_datetime_to_json(self.created_at)
        updated_at = util.parse_datetime_to_json(self.updated_at)
        return {
            "title": self.title,
            "feed": self.feed,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    def _gather_episodes(self) -> List[Episode]:
        """Traverses the file system to locate episodes for this podcast tracked in the
        pod store.

        Any file in the right file system location that ends with with the appropriate
        file extension (`.episode.json`) will be treated as an episode file and loaded
        into a `pod_store.episode.Episode` object.

        Note that this is a generator function. It can be consumed lazily or cast into a
        list to get a complete listing.
        """
        if not os.path.exists(self.store_episodes_path):
            return []

        for episode_file in os.listdir(self.store_episodes_path):
            if not episode_file.endswith(STORE_EPISODE_FILE_EXTENSION):
                continue
            store_file_path = os.path.join(self.store_episodes_path, episode_file)
            yield Episode.from_store_file(
                store_file_path=store_file_path,
                base_download_path=self._downloads_path,
            )

    def _get_episode_store_file_path_from_id(self, store_id: str) -> str:
        """Determine the file path in the pod store for a podcast episode based on
        store ID."""
        file_name = f"{store_id}{STORE_EPISODE_FILE_EXTENSION}"
        return os.path.join(self.store_episodes_path, file_name)

    def _parse_episode_feed_data(
        self,
        listing_number: int,
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

        Determines a download URL from the available links in the RSS feed data.

        Converts the `published` and `updated` data from the RSS feed into `datetime`
        objects.
        """
        updated_parsed = updated_parsed or published_parsed

        episode_number = (
            itunes_episode
            or self._parse_episode_number_from_rss_title(title)
            or str(listing_number)
        )

        return {
            "id": self._parse_store_episode_id(id),
            "episode_number": episode_number.rjust(4, "0"),
            "title": title,
            "url": [
                u["href"] for u in links if u["type"] in ("audio/mpeg", "audio/mp3")
            ][0],
            "created_at": datetime(*published_parsed[:6]),
            "updated_at": datetime(*updated_parsed[:6]),
        }

    @staticmethod
    def _parse_episode_number_from_rss_title(rss_title: str) -> str:
        stripped_title = re.sub(r"[^A-Za-z0-9 ]+", "", rss_title)
        title_tokens = stripped_title.split()
        start_token, end_token = title_tokens[0], title_tokens[-1]

        if start_token.isdigit():
            return start_token
        elif end_token.isdigit():
            return end_token

    @staticmethod
    def _parse_store_episode_id(rss_id: str) -> str:
        return rss_id.split("/")[-1]
