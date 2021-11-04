"""Podcast episodes tracked in the pod store.

Episode objects are created/managed using the `pod_store.podcasts.PodcastEpisodes`
class.
"""
import math
import os
import re
from datetime import datetime
from typing import Any, List, Optional, Type, TypeVar

import music_tag
import requests

from . import DO_NOT_SET_EPISODE_METADATA, util

DOWNLOAD_CHUNK_SIZE = 2000

E = TypeVar("E", bound="Episode")
P = TypeVar("Podcast")


class EpisodeDownloadManager:
    """Contextmanager class for handling podcast episode downloads.

    Makes the download request and writes the data to the file system.

    Determines how many chunks of data will be involved (for use by progress bars or other
    status indicators).

    After the download is complete, it sets the episode's downloaded-at timestamp,
    untags it as `new`, and sets the audio file metadata.
    """

    def __init__(self, episode: E) -> None:
        self._episode = episode

        os.makedirs(os.path.dirname(episode.download_path), exist_ok=True)
        self._response = requests.get(episode.url, stream=True)

        try:
            self.number_of_chunks = math.ceil(
                self._response.headers["content-length"] / DOWNLOAD_CHUNK_SIZE
            )
        except (KeyError, TypeError):
            self.number_of_cunks = None

    def __enter__(self):
        with open(self._episode.download_path, "wb") as f:
            for chunk in self._response.iter_content(DOWNLOAD_CHUNK_SIZE):
                f.write(chunk)
                yield

    def __exit__(self, *args, **kwargs):
        self._episode.downloaded_at = datetime.utcnow()
        self._episode.untag("new")
        self._episode.set_audio_file_metadata()


class Episode:
    """Podcast episode tracked in the store.

    podcast (pod_store.podcasts.Podcast): podcast this episode belongs to
    id (str): store ID (parsed from RSS feed ID)
    episode_number (str): zero-padded episode number from podcast feed
    title (str): episode title
    short_description (str): short description of episode
    long_description (str): longer description of episode
    url (str): download URL
    tags (list): arbitrary text tags. `new` tag is used to determine if an episode has
        been downloaded yet.
    downloaded_at (datetime): if set to `None`, the episode hasn't been downloaded yet

    created_at (datetime)
    updated_at (datetime)
    """

    def __init__(
        self,
        podcast: P,
        id: str,
        episode_number: str,
        title: str,
        short_description: str,
        long_description: str,
        url: str,
        created_at: datetime,
        updated_at: datetime,
        tags: List[str] = None,
        downloaded_at: Optional[datetime] = None,
    ) -> None:
        self.podcast = podcast

        self.id = id
        self.episode_number = episode_number
        self.title = title
        self.short_description = short_description
        self.long_description = long_description
        self.url = url
        self.tags = tags or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.downloaded_at = downloaded_at

    @classmethod
    def from_json(
        cls: Type[E],
        created_at: str,
        updated_at: str,
        downloaded_at: Optional[str] = None,
        **kwargs,
    ) -> E:
        """Load a `pod_store.episodes.Episode` object from json data.

        Parses `datetime` objects from json strings where appropriate.
        """
        created_at = util.parse_datetime_from_json(created_at)
        updated_at = util.parse_datetime_from_json(updated_at)
        downloaded_at = util.parse_datetime_from_json(downloaded_at)

        return cls(
            created_at=created_at,
            updated_at=updated_at,
            downloaded_at=downloaded_at,
            **kwargs,
        )

    def __eq__(self, other: Any) -> bool:
        try:
            other_json = other.to_json()
        except AttributeError:
            return False
        return self.to_json() == other_json

    def __repr__(self) -> str:
        return f"Episode({self.episode_number}, {self.title})"

    @property
    def download_path(self) -> str:
        """Determines the download path for this episode, based on the podcast's
        download location.

        The filename is built from the episode number and a lowercase version of the
        title that has had non-alphanumeric characters replaced with a dash. This helps
        with filename consistency and removes characters that lead to problems on some
        device filesystems (such as the one on my cheap MP3 player).

        The file type extension is determined from the download URL.
        """
        lowercase_title = self.title.lower()
        cleaned_title = re.sub(r"[^a-zA-Z0-9]", "-", lowercase_title)
        file_type = os.path.splitext(self.url)[1][:4]
        return os.path.join(
            self.podcast.episode_downloads_path,
            f"{self.episode_number}-{cleaned_title}{file_type}",
        )

    def download(self) -> None:
        """Download the audio file of the episode to the file system."""
        return EpisodeDownloadManager(episode=self)

    def set_audio_file_metadata(self) -> None:
        """Helper to set metadata on the downloaded MP3 file.

        Matches the following audio metadata tags to the values:

            artist        -> episode.podcast.title
            album_artist

            title         -> episode.title
            track_title

            genre         -> "Podcast"

            track_number  -> episode.episode_number
            year          -> episode.created_at.year

        Setting the `DO_NOT_SET_POD_STORE_EPISODE_METADATA` env var will stop this
        behavior.
        """
        if DO_NOT_SET_EPISODE_METADATA:
            return

        f = music_tag.load_file(self.download_path)
        f["artist"] = self.podcast.title
        f["album"] = self.podcast.title
        f["album_artist"] = self.podcast.title
        f["title"] = self.title
        f["track_title"] = self.title
        f["genre"] = "Podcast"
        f["track_number"] = self.episode_number
        f["year"] = self.created_at.year
        f.save()

    def update(self, **data: Any) -> None:
        """Update arbitrary attributes by passing in a dict."""
        for key, value in data.items():
            setattr(self, key, value)

    def tag(self, tag_name: str) -> None:
        """Apply a tag to the episode."""
        self.tags.append(tag_name)

    def untag(self, tag_name: str) -> None:
        """Remove a tag from the episode."""
        self.tags = [t for t in self.tags if t != tag_name]

    def to_json(self) -> dict:
        """Convert episode data into a json-able dict.

        Parses datetime fields into isoformat strings for json storage.
        """
        created_at = util.parse_datetime_to_json(self.created_at)
        updated_at = util.parse_datetime_to_json(self.updated_at)
        downloaded_at = util.parse_datetime_to_json(self.downloaded_at)

        return {
            "id": self.id,
            "episode_number": self.episode_number,
            "title": self.title,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "url": self.url,
            "tags": self.tags,
            "created_at": created_at,
            "updated_at": updated_at,
            "downloaded_at": downloaded_at,
        }
