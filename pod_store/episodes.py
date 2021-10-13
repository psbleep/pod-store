import os
from datetime import datetime
from typing import Any, Optional, Type, TypeVar

import requests

from . import util

DOWNLOAD_CHUNK_SIZE = 2000

E = TypeVar("E", bound="Episode")


class Episode:
    """Podcast episode tracked in the store.

    id (str): store ID (parsed from RSS feed ID)
    download_path (str): where episode will be downloaded on file system
    episode_number (str): zero-padded episode number from podcast feed
    title (str): episode title
    url (str): download URL
    downloaded_at (datetime): if set to `None`, the episode hasn't been downloaded yet

    created_at (datetime)
    updated_at (datetime)
    """

    def __init__(
        self,
        id: str,
        download_path: str,
        episode_number: str,
        title: str,
        url: str,
        created_at: datetime,
        updated_at: datetime,
        downloaded_at: Optional[datetime] = None,
    ):
        self.id = id
        self.download_path = download_path
        self.episode_number = episode_number
        self.title = title
        self.url = url
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

    def __str__(self) -> str:
        if self.downloaded_at:
            downloaded_msg = "[X]"
        else:
            downloaded_msg = ""
        return f"[{self.episode_number}] {self.title} {downloaded_msg}"

    def download(self) -> None:
        """Download the audio file of the episode to the file system."""
        os.makedirs(os.path.dirname(self.download_path), exist_ok=True)

        resp = requests.get(self.url, stream=True)
        with open(self.download_path, "wb") as f:
            for chunk in resp.iter_content(DOWNLOAD_CHUNK_SIZE):
                f.write(chunk)
        self.mark_as_downloaded()

    def mark_as_downloaded(self) -> None:
        """Mark the episode as 'already downloaded'."""
        self.downloaded_at = datetime.utcnow()

    def update(self, **data: Any) -> None:
        """Update arbitrary attributes by passing in a dict."""
        for key, value in data.items():
            setattr(self, key, value)

    def to_json(self) -> dict:
        """Convert episode data into a json-able dict.

        Parses datetime fields into isoformat strings for json storage.
        """
        created_at = util.parse_datetime_to_json(self.created_at)
        updated_at = util.parse_datetime_to_json(self.updated_at)
        downloaded_at = util.parse_datetime_to_json(self.downloaded_at)

        return {
            "id": self.id,
            "download_path": self.download_path,
            "episode_number": self.episode_number,
            "title": self.title,
            "url": self.url,
            "created_at": created_at,
            "updated_at": updated_at,
            "downloaded_at": downloaded_at,
        }
