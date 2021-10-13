import json
import os
from typing import List, Optional

from .exc import PodcastDoesNotExistError, PodcastExistsError, StoreExistsError
from .podcasts import Podcast
from .util import run_git_command


class StoreFileHandler:
    def __init__(self, store_file_path):
        self._store_file_path = store_file_path

    @classmethod
    def create_with_file(cls, store_file_path: str):
        file_handler = cls(store_file_path)
        file_handler.write_data({})
        return file_handler

    def read_data(self):
        with open(self._store_file_path) as f:
            return json.load(f)

    def write_data(self, data: dict):
        with open(self._store_file_path, "w") as f:
            json.dump(data, f)

    def __repr__(self):
        return "<StoreFileHandler({self._store_file_path!r})>"


class Store:
    def __init__(
        self,
        store_path: str,
        podcast_downloads_path: str,
        file_handler: StoreFileHandler,
    ) -> None:
        self._store_path = store_path
        self._podcast_downloads_path = podcast_downloads_path

        self._file_handler = file_handler

        podcast_data = file_handler.read_data()
        self.podcasts = StorePodcasts(
            podcast_data=podcast_data, podcast_downloads_path=podcast_downloads_path
        )

    @classmethod
    def create(
        cls,
        store_path: str,
        store_file_path: str,
        podcast_downloads_path: str,
        setup_git: bool,
        git_url: Optional[str] = None,
        store_file_handler_cls: StoreFileHandler = StoreFileHandler,
    ):
        try:
            os.makedirs(store_path)
        except FileExistsError:
            raise StoreExistsError(store_path)
        os.makedirs(podcast_downloads_path, exist_ok=True)

        file_handler = store_file_handler_cls.create_with_file(store_file_path)

        if setup_git:
            run_git_command("init")
            if git_url:
                run_git_command(f"remote add origin {git_url}")
        return cls(
            store_path=store_path,
            podcast_downloads_path=podcast_downloads_path,
            file_handler=file_handler,
        )

    def save(self):
        podcast_data = self.podcasts.to_json()
        self._file_handler.write_data(podcast_data)

    def __repr__(self):
        return f"<Store({self._store_path!r})>"


class StorePodcasts:
    def __init__(self, podcast_data: dict, podcast_downloads_path: str):
        self._podcasts = {
            title: Podcast.from_json(**podcast)
            for title, podcast in podcast_data.items()
        }
        self._podcast_downloads_path = podcast_downloads_path

    def add(
        self,
        title: str,
        episode_downloads_path: Optional[str] = None,
        episode_data: Optional[dict] = None,
        **kwargs,
    ) -> None:
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
        try:
            del self._podcasts[title]
        except KeyError:
            raise PodcastDoesNotExistError(title)

    def get(self, title: str) -> Podcast:
        try:
            return self._podcasts[title]
        except KeyError:
            raise PodcastDoesNotExistError(title)

    def list(self, **filters) -> List[Podcast]:
        podcasts = [p for p in self._podcasts.values()]
        for key, value in filters.items():
            podcasts = [p for p in podcasts if getattr(p, key) == value]
        return sorted(podcasts, key=lambda p: p.created_at)

    def rename(self, old_title: str, new_title: str) -> None:
        if new_title in self._podcasts:
            raise PodcastExistsError(new_title)

        podcast = self.get(old_title)
        podcast.episode_downloads_path = os.path.join(
            self._podcast_downloads_path, new_title
        )
        self._podcasts[new_title] = podcast
        del self._podcasts[old_title]

    def to_json(self):
        return {title: podcast.to_json() for title, podcast in self._podcasts.items()}

    def __repr__(self):
        return "<StorePodcasts>"
