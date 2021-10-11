import json
import os
from datetime import datetime
from typing import Any, Optional, Type, TypeVar

import requests

from . import util
from .exc import EpisodeDoesNotExistError

DOWNLOAD_CHUNK_SIZE = 2000


E = TypeVar("E", bound="Episode")


class Episode:
    """Podcast episode tracked in the pypod store.

    _store_file_path: file path for the episode file in the pypod store
    _download_path: file path to download the episode audio file

    id: store ID (parsed from RSS feed ID)
    episode_number: zero-padded episode number
    title: episode title
    url: download URL
    downloaded_at: if set to `None`, the episode hasn't been downloaded yet
    created_at: timestamp
    updated_at: timestamp
    """

    def __init__(
        self,
        store_file_path: str,
        base_download_path: str,
        id: str,
        episode_number: str,
        title: str,
        url: str,
        created_at: datetime,
        updated_at: datetime,
        downloaded_at: Optional[datetime] = None,
    ):
        self._store_file_path = store_file_path

        download_file_name = f"{episode_number}-{title}.mp3"
        self._download_path = os.path.join(base_download_path, download_file_name)

        self.id = id
        self.episode_number = episode_number
        self.title = title
        self.url = url
        self.created_at = created_at
        self.updated_at = updated_at
        self.downloaded_at = downloaded_at

    def __eq__(self, other: Any) -> bool:
        try:
            other_json = other.to_json()
        except AttributeError:
            return False
        return self.to_json() == other_json

    def __repr__(self) -> str:
        return f"Episode({self.to_json()})"

    @classmethod
    def from_store_file(
        cls: Type[E], store_file_path: str, base_download_path: str
    ) -> E:
        """Instantiates an `Episode` object from the contents of a json file.

        Parses datetime information from the json file into `datetime` objects.
        """
        try:
            with open(store_file_path) as f:
                episode_data = json.load(f)
        except FileNotFoundError:
            raise EpisodeDoesNotExistError(store_file_path)

        created_at = util.parse_datetime_from_json(episode_data.pop("created_at"))
        updated_at = util.parse_datetime_from_json(episode_data.pop("updated_at"))
        downloaded_at = util.parse_datetime_from_json(episode_data.pop("downloaded_at"))

        return cls(
            store_file_path=store_file_path,
            base_download_path=base_download_path,
            created_at=created_at,
            updated_at=updated_at,
            downloaded_at=downloaded_at,
            **episode_data,
        )

    def download(self) -> None:
        """Download the audio file of the episode to the file system."""
        os.makedirs(os.path.dirname(self._download_path), exist_ok=True)

        resp = requests.get(self.url, stream=True)
        with open(self._download_path, "wb") as f:
            for chunk in resp.iter_content(DOWNLOAD_CHUNK_SIZE):
                f.write(chunk)
        self.downloaded_at = datetime.utcnow()
        self.save()

    def mark_as_downloaded(self) -> None:
        """Mark the episode as 'already downloaded'."""
        self.downloaded_at = datetime.utcnow()
        self.save()

    def update(self, **data: Any) -> None:
        """Update arbitrary attributes by passing in a dict."""
        for key, value in data.items():
            setattr(self, key, value)

    def save(self) -> None:
        """Save episode data to a json file in the pypod store."""
        with open(self._store_file_path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

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
            "url": self.url,
            "created_at": created_at,
            "updated_at": updated_at,
            "downloaded_at": downloaded_at,
        }
