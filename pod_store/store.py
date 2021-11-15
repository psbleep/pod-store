"""Store that tracks your podcasts.

Store data for all podcasts (and associated episodes) is persisted in a JSON file.

Reading/writing to the store file is delegated to the classes in the
`store_file_handlers` module.
"""
import os
from typing import List, Optional

from . import GPG_ID_FILE_PATH, PODCAST_DOWNLOADS_PATH, get_store_file_path
from .exc import (
    PodcastDoesNotExistError,
    PodcastExistsError,
    StoreExistsError,
    StoreIsNotEncrypted,
)
from .podcasts import Podcast
from .store_file_handlers import (
    EncryptedStoreFileHandler,
    StoreFileHandler,
    UnencryptedStoreFileHandler,
)
from .util import run_git_command, run_shell_command


class StorePodcasts:
    """Class for tracking all the podcasts in the store.

    _podcasts (dict):
        {title: `pod_store.podcasts.Podcast`}
    """

    def __init__(self, podcast_data: dict) -> None:
        self._podcasts = {
            title: Podcast.from_json(**podcast)
            for title, podcast in podcast_data.items()
        }

    def __repr__(self) -> str:
        return "<StorePodcasts>"

    def add(
        self,
        title: str,
        episode_data: Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Add a podcast to the store."""
        if title in self._podcasts:
            raise PodcastExistsError(title)
        episode_data = episode_data or {}

        podcast = Podcast(
            title=title,
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

    def list(self) -> List[Podcast]:
        """Return a list of podcasts, sorted by time created (oldest first)."""
        podcasts = [p for p in self._podcasts.values()]
        return sorted(podcasts, key=lambda p: p.created_at)

    def rename(self, old_title: str, new_title: str) -> None:
        """Rename a podcast in the store.

        Will change the podcast's episode download path in accordance with the new title
        """
        if new_title in self._podcasts:
            raise PodcastExistsError(new_title)

        podcast = self.get(old_title)
        podcast.title = new_title
        self._podcasts[new_title] = podcast
        del self._podcasts[old_title]

    def to_json(self) -> dict:
        """Convert store podcasts to json data for writing to the store file."""
        return {title: podcast.to_json() for title, podcast in self._podcasts.items()}


class Store:
    """Podcast store coordinating class.

    podcasts (StorePodcasts): tracks all the podcasts kept in the store

    _store_path (str): location of pod store directory

    _file_handler (StoreFileHandler): class that handles reading/writing from the store
        json file
    """

    def __init__(
        self,
        store_path: str,
        file_handler: StoreFileHandler,
    ) -> None:
        self._store_path = store_path
        self._file_handler = file_handler

        podcast_data = self._file_handler.read_data()
        self.podcasts = StorePodcasts(podcast_data=podcast_data)

    @classmethod
    def init(
        cls,
        store_path: str,
        store_file_name: str,
        setup_git: bool,
        git_url: Optional[str] = None,
        gpg_id: Optional[str] = None,
    ) -> None:
        """Initialize a new pod store.

        Optionally set up the `git` repo for the store.

        Optionally set the GPG ID for store encryption and establish the store file
        as an encrypted file.
        """
        store_file_path = os.path.join(store_path, store_file_name)
        gitignore_file_path = os.path.join(store_path, ".gitignore")

        os.makedirs(PODCAST_DOWNLOADS_PATH, exist_ok=True)

        if git_url:
            cls._setup_existing_repo(git_url, store_path, gpg_id=gpg_id)
        else:
            try:
                os.makedirs(store_path)
            except FileExistsError:
                raise StoreExistsError(store_path)

            if setup_git:
                run_git_command("init")

                with open(gitignore_file_path, "w") as f:
                    f.write(".gpg-id")

        if gpg_id:
            cls._setup_encrypted_store(gpg_id=gpg_id, store_file_path=store_file_path)
        else:
            cls._setup_unencrypted_store(store_file_path)

    def __repr__(self) -> str:
        return f"<Store({self._store_path!r})>"

    def encrypt(self, gpg_id: str) -> None:
        """Encrypt an existing store that is currently stored in plaintext."""
        existing_store_file_path = self._file_handler.store_file_path
        store_data = self._file_handler.read_data()
        encrypted_store_file_path = get_store_file_path(gpg_id=gpg_id)
        self._setup_encrypted_store(
            gpg_id=gpg_id,
            store_file_path=encrypted_store_file_path,
            store_data=store_data,
            overwrite_existing=True,
        )
        if encrypted_store_file_path != existing_store_file_path:
            os.remove(existing_store_file_path)

    def unencrypt(self) -> None:
        """Unencrypt an existing store that is currently stored as encrypted data.

        Unsets the GPG ID for the store and writes the existing encrypted store data
        as plaintext json.
        """
        if not os.path.exists(GPG_ID_FILE_PATH):
            raise StoreIsNotEncrypted(GPG_ID_FILE_PATH)
        existing_store_file_path = self._file_handler.store_file_path
        store_data = self._file_handler.read_data()
        unencrypted_store_file_path = get_store_file_path(gpg_id=None)
        self._setup_unencrypted_store(
            store_file_path=unencrypted_store_file_path,
            store_data=store_data,
            overwrite_existing=True,
        )
        if existing_store_file_path != unencrypted_store_file_path:
            os.remove(existing_store_file_path)

    def save(self) -> None:
        """Save data to the store json file."""
        podcast_data = self.podcasts.to_json()
        self._file_handler.write_data(podcast_data)

    @staticmethod
    def _setup_existing_repo(
        git_url: str, store_path: str, gpg_id: Optional[str] = None
    ) -> None:
        run_shell_command(f"git clone {git_url} {store_path}")
        if gpg_id:
            with open(os.path.join(GPG_ID_FILE_PATH), "w") as f:
                f.write(gpg_id)

    @staticmethod
    def _setup_encrypted_store(
        gpg_id: str,
        store_file_path: str,
        store_data: dict = None,
        overwrite_existing: bool = False,
    ) -> None:
        """Set up the store as a GPG encrypted store.

        Sets the GPG ID that will be used by the store, and writes the store data
        passed in as GPG encrypted data to the store file.
        """
        store_data = store_data or {}

        with open(os.path.join(GPG_ID_FILE_PATH), "w") as f:
            f.write(gpg_id)

        if not os.path.exists(store_file_path) or overwrite_existing:
            EncryptedStoreFileHandler.create_store_file(
                gpg_id=gpg_id, store_file_path=store_file_path, store_data=store_data
            )

    @staticmethod
    def _setup_unencrypted_store(
        store_file_path: str, store_data: dict = None, overwrite_existing: bool = False
    ) -> None:
        store_data = store_data or {}

        if not os.path.exists(store_file_path) or overwrite_existing:
            UnencryptedStoreFileHandler.create_store_file(
                store_file_path, store_data=store_data
            )

        if os.path.exists(GPG_ID_FILE_PATH):
            os.remove(GPG_ID_FILE_PATH)
