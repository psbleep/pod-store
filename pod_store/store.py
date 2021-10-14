import os
from typing import List, Optional

from . import GPG_ID_FILE_PATH
from .exc import (
    NoPodcastsFoundError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    StoreExistsError,
)
from .podcasts import Podcast
from .store_file_handlers import (
    EncryptedStoreFileHandler,
    StoreFileHandler,
    UnencryptedStoreFileHandler,
)
from .util import run_git_command


class StorePodcasts:
    """Class for tracking all the podcasts in the store.

    _podcast_downloads_path (str): file system location for podcasts to download
        episodes to

    _podcasts (dict):
        {title: `pod_store.podcasts.Podcast`}
    """

    def __init__(self, podcast_downloads_path: str, podcast_data: dict):
        self._podcast_downloads_path = podcast_downloads_path

        self._podcasts = {
            title: Podcast.from_json(**podcast)
            for title, podcast in podcast_data.items()
        }

    def __repr__(self):
        return "<StorePodcasts>"

    def add(
        self,
        title: str,
        episode_downloads_path: Optional[str] = None,
        episode_data: Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Add a podcast to the store.

        An `episodes_download_path` for the podcast object  will be constructed from the
        `_podcast_downloads_path` attribute and the title passed in, if none is
        provided.
        """
        if title in self._podcasts:
            raise PodcastExistsError(title)

        episode_downloads_path = episode_downloads_path or os.path.join(
            self._podcast_downloads_path, title
        )
        episode_data = episode_data or {}
        podcast = Podcast(
            title=title,
            episode_downloads_path=episode_downloads_path,
            episode_data=episode_data,
            **kwargs,
        )
        podcast.refresh()
        self._podcasts[title] = podcast
        return podcast

    def delete(self, title: str) -> None:
        """Delete a podcast from the store.

        Looks up podcast by title.
        """
        try:
            del self._podcasts[title]
        except KeyError:
            raise PodcastDoesNotExistError(title)

    def get(self, title: str) -> Podcast:
        """Retrieve a podcast from the store.

        Looks up podcast by title.
        """
        try:
            return self._podcasts[title]
        except KeyError:
            raise PodcastDoesNotExistError(title)

    def list(self, allow_empty: bool = True, **filters) -> List[Podcast]:
        """Return a list of podcasts, sorted by time created (oldest first).

        When `allow_empty` is set to `False`, an exception will be raised if no podcasts
        are found.

        Optionally provide a list of keyword arguments to filter results by.

            list(foo="bar")

        will check for a `foo` attribute on the `pod_store.podcasts.Podcast` object and
        check if the value matches "bar".
        """
        podcasts = [p for p in self._podcasts.values()]
        for key, value in filters.items():
            podcasts = [p for p in podcasts if getattr(p, key) == value]
        if not podcasts and not allow_empty:
            raise NoPodcastsFoundError()
        return sorted(podcasts, key=lambda p: p.created_at)

    def rename(self, old_title: str, new_title: str) -> None:
        """Rename a podcast in the store.

        Will change the podcast's episode download path in accordance with the new title
        """
        if new_title in self._podcasts:
            raise PodcastExistsError(new_title)

        podcast = self.get(old_title)
        podcast.episode_downloads_path = os.path.join(
            self._podcast_downloads_path, new_title
        )
        self._podcasts[new_title] = podcast
        del self._podcasts[old_title]

    def to_json(self):
        """Convert store podcasts to json data for writing to the store file."""
        return {title: podcast.to_json() for title, podcast in self._podcasts.items()}


class Store:
    """Podcast store coordinating class.

    podcasts (StorePodcasts): tracks all the podcasts kept in the store

    _store_path (str): location of pod store directory

    _podcast_downloads_path (str): file system directory for podcasts to download
        episodes into

    _file_handler (StoreFileHandler): class that handles reading/writing from the store
        json file
    """

    def __init__(
        self,
        store_path: str,
        podcast_downloads_path: str,
        file_handler: StoreFileHandler,
    ) -> None:
        self._store_path = store_path
        self._podcast_downloads_path = podcast_downloads_path

        self._file_handler = file_handler

        podcast_data = self._file_handler.read_data()
        self.podcasts = StorePodcasts(
            podcast_data=podcast_data, podcast_downloads_path=podcast_downloads_path
        )

    @classmethod
    def init(
        cls,
        store_path: str,
        store_file_path: str,
        podcast_downloads_path: str,
        setup_git: bool,
        git_url: Optional[str] = None,
        gpg_id: Optional[str] = None,
    ):
        """Initialize a new pod store.

        Optionally set up the `git` repo for the store.

        Optionally set the GPG ID for store encryption and establish the store file
        as an encrypted file.
        """
        try:
            os.makedirs(store_path)
        except FileExistsError:
            raise StoreExistsError(store_path)
        os.makedirs(podcast_downloads_path, exist_ok=True)

        if setup_git:
            run_git_command("init")
            if git_url:
                run_git_command(f"remote add origin {git_url}")
            with open(os.path.join(store_path, ".gitignore"), "w") as f:
                f.write(".gpg-id")

        if gpg_id:
            cls._setup_encrypted_store(gpg_id=gpg_id, store_file_path=store_file_path)
        else:
            UnencryptedStoreFileHandler.create_store_file(store_file_path)

    def __repr__(self):
        return f"<Store({self._store_path!r})>"

    def encrypt(self, gpg_id: str):
        """Encrypt an existing store that is currently stored in plaintext."""
        store_file_path = self._file_handler.store_file_path
        store_data = self._file_handler.read_data()
        self._setup_encrypted_store(
            gpg_id=gpg_id, store_file_path=store_file_path, store_data=store_data
        )

    def unencrypt(self):
        """Unencrypt an existing store that is currently stored as encrypted data.

        Unsets the GPG ID for the store and writes the existing encrypted store data
        as plaintext json.
        """
        store_file_path = self._file_handler.store_file_path
        store_data = self._file_handler.read_data()
        UnencryptedStoreFileHandler.create_store_file(
            store_file_path=store_file_path, store_data=store_data
        )
        os.remove(GPG_ID_FILE_PATH)

    def save(self):
        """Save data to the store json file."""
        podcast_data = self.podcasts.to_json()
        self._file_handler.write_data(podcast_data)

    @staticmethod
    def _setup_encrypted_store(
        gpg_id: str, store_file_path: str, store_data: dict = None
    ):
        """Set up the store as a GPG encrypted store.

        Sets the GPG ID that will be used by the store, and writes the store data
        passed in as GPG encrypted data to the store file.
        """
        with open(os.path.join(GPG_ID_FILE_PATH), "w") as f:
            f.write(gpg_id)
        EncryptedStoreFileHandler.create_store_file(
            gpg_id=gpg_id, store_file_path=store_file_path, store_data=store_data
        )
