import json
import os
from datetime import datetime
from unittest.mock import call

import pytest

from pod_store import store
from pod_store.exc import PodcastDoesNotExistError, PodcastExistsError, StoreExistsError

from . import TEST_STORE_PATH


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.store.run_git_command")


def _get_podcast_titles(podcasts):
    return [p.title for p in podcasts]


def test_init_store(start_with_no_store):
    store.init_store(setup_git=False)

    assert os.path.exists(TEST_STORE_PATH)


def test_init_store_setup_git(start_with_no_store, mocked_run_git_command):
    store.init_store(setup_git=True)
    mocked_run_git_command.assert_called_with("init")


def test_init_store_setup_git_with_git_url(start_with_no_store, mocked_run_git_command):
    store.init_store(setup_git=True, git_url="https://git.foo.bar/pod_store-store.git")
    mocked_run_git_command.assert_has_calls(
        [
            call("init"),
            call("remote add origin https://git.foo.bar/pod_store-store.git"),
        ]
    )


def test_init_store_already_exists():
    with pytest.raises(StoreExistsError):
        store.init_store()


def test_store_list_podcasts():
    assert _get_podcast_titles(store.list_podcasts()) == ["a/1", "b", "c/2", "c/d/3"]


def test_store_search_podcasts():
    assert _get_podcast_titles(store.search_podcasts("c/")) == ["c/2", "c/d/3"]


def test_store_podcasts_with_new_episodes():
    assert _get_podcast_titles(store.list_podcasts_with_new_episodes()) == ["b"]


def test_store_get_podcast():
    assert store.get_podcast("c/d/3").title == "c/d/3"


def test_store_add_podcast():
    now = datetime.utcnow()
    file_path = os.path.join(TEST_STORE_PATH, "e/4.podcast.json")
    store.add_podcast(
        title="e/4", feed="https://www.py.pod/rss", created_at=now, updated_at=now
    )

    with open(file_path) as f:
        assert json.load(f) == {
            "title": "e/4",
            "feed": "https://www.py.pod/rss",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }


def test_store_add_podcast_title_already_exists():
    with pytest.raises(PodcastExistsError):
        store.add_podcast(title="a/1", feed="https://a1.cast/rss")


def test_store_remove_podcast():
    file_path = os.path.join(TEST_STORE_PATH, "c/2.podcast.json")
    store.remove_podcast("c/2")

    assert not os.path.exists(file_path)


def test_store_rename_podcast():
    new_podcast_path = os.path.join(TEST_STORE_PATH, "z/foo.podcast.json")
    old_podcast_path = os.path.join(TEST_STORE_PATH, "c/2.podcast.json")

    new_podcast_episodes_path = os.path.join(TEST_STORE_PATH, "z/foo")

    store.rename_podcast("c/2", "z/foo")

    assert not os.path.exists(old_podcast_path)

    assert os.path.exists(new_podcast_path)
    assert os.path.exists(new_podcast_episodes_path)

    with open(new_podcast_path) as f:
        assert json.load(f)["title"] == "z/foo"


def test_store_rename_podcast_does_not_exist():
    with pytest.raises(PodcastDoesNotExistError):
        store.rename_podcast("zzzzzz", "aaaaa")


def test_store_rename_podcast_new_title_already_exists():
    with pytest.raises(PodcastExistsError):
        store.rename_podcast("c/2", "a/1")
