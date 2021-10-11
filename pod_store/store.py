import os
import shutil
from datetime import datetime
from typing import List, Optional

from . import DOWNLOADS_PATH, STORE_PATH, STORE_PODCAST_FILE_EXTENSION
from .exc import PodcastDoesNotExistError, PodcastExistsError, StoreExistsError
from .podcast import Podcast
from .util import run_git_command


def init_store(setup_git: bool = True, git_url: Optional[str] = None):
    try:
        os.makedirs(STORE_PATH)
    except FileExistsError:
        raise StoreExistsError(STORE_PATH)
    os.makedirs(DOWNLOADS_PATH, exist_ok=True)

    if setup_git:
        run_git_command("init")
        if git_url:
            run_git_command(f"remote add origin {git_url}")


def list_podcasts() -> List[Podcast]:
    """Lists all podcasts tracked in the pypod store."""
    return sorted(list(_gather_podcasts()), key=lambda p: p.title)


def list_podcasts_with_new_episodes() -> List[Podcast]:
    """List only podcasts tracked in the store with new episodes."""
    return [p for p in list_podcasts() if p.has_new_episodes]


def search_podcasts(term: str) -> List[Podcast]:
    """Search the store for podcasts with the search term in the title."""
    return [p for p in list_podcasts() if term in p.title]


def get_podcast(title: str) -> Podcast:
    """Find a podcast in the store by title."""
    return Podcast.from_store_file(_get_podcast_file_path_from_title(title))


def add_podcast(
    title: str,
    feed: str,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> None:
    """Add a podcast to the store with the data provided.

    `created_at` and `updated_at` will be set to the current datetime if not provided.
    """
    created_at = created_at or datetime.utcnow()
    updated_at = updated_at or datetime.utcnow()

    store_file_path = _get_podcast_file_path_from_title(title)
    if os.path.exists(store_file_path):
        raise PodcastExistsError(title)
    os.makedirs(os.path.dirname(store_file_path), exist_ok=True)

    podcast = Podcast(
        store_file_path=store_file_path,
        title=title,
        feed=feed,
        created_at=created_at,
        updated_at=updated_at,
    )
    podcast.save()
    podcast.refresh()


def remove_podcast(title: str) -> None:
    """Remove podcast from the store by title."""
    store_file_path = _get_podcast_file_path_from_title(title)
    podcast = Podcast.from_store_file(store_file_path)

    try:
        shutil.rmtree(podcast.store_episodes_path)
    except FileNotFoundError:
        pass
    os.remove(store_file_path)


def rename_podcast(old_title: str, new_title: str) -> None:
    """Rename a podcast in the store."""
    old_path = _get_podcast_file_path_from_title(old_title)
    old_podcast_episodes_path = get_podcast(old_title).store_episodes_path

    new_path = _get_podcast_file_path_from_title(new_title)
    if os.path.exists(new_path):
        raise PodcastExistsError(new_title)
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    try:
        os.rename(old_path, new_path)
    except FileNotFoundError:
        raise PodcastDoesNotExistError(old_title)

    podcast = get_podcast(new_title)
    podcast.title = new_title
    podcast.save()

    if os.path.exists(old_podcast_episodes_path):
        shutil.move(old_podcast_episodes_path, podcast.store_episodes_path)


def _gather_podcasts() -> Podcast:
    """Traverses the file system to locate podcasts tracked in the pypod store.

    Any file that ends with the appropriate file extension (`.podcast.json`) will be
    treated as a podcast file and loaded into a `pypod.podcast.Podcast` object.

    Note that this is a generator function. It can be consumed lazily or cast into a
    list to get a complete listing.
    """
    for parent, _, files in os.walk(STORE_PATH):
        for file_name in files:
            if not file_name.endswith(STORE_PODCAST_FILE_EXTENSION):
                continue
            store_file_path = os.path.abspath(os.path.join(parent, file_name))
            yield Podcast.from_store_file(store_file_path)


def _get_podcast_file_path_from_title(title: str) -> str:
    """Determine the file path in the pypod store for a podcast
    based on podcast title."""
    return os.path.join(STORE_PATH, f"{title}{STORE_PODCAST_FILE_EXTENSION}")
