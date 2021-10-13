import json
import os
import shutil

from datetime import datetime, timedelta

import pytest

from pod_store.store import Store, StoreFileHandler
from tests import (
    TEST_DOWNLOAD_PATH,
    TEST_PODCAST_DOWNLOAD_PATH,
    TEST_STORE_FILE_PATH,
    TEST_STORE_PATH,
)


# Autouse to establish fresh store data for every test.
@pytest.fixture(autouse=True)
def setup_test_store_data_and_downloads_path(request, store_podcasts_data):
    def cleanup():
        if os.path.exists(TEST_STORE_PATH):
            shutil.rmtree(TEST_STORE_PATH)
        if os.path.exists(TEST_DOWNLOAD_PATH):
            shutil.rmtree(TEST_DOWNLOAD_PATH)

    cleanup()

    os.makedirs(TEST_STORE_PATH)
    os.makedirs(TEST_DOWNLOAD_PATH)
    with open(TEST_STORE_FILE_PATH, "w") as f:
        json.dump(store_podcasts_data, f, indent=2)
    request.addfinalizer(cleanup)


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_feedparser_parse(mocker):
    return mocker.patch("pod_store.podcasts.feedparser.parse")


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_requests_get(mocker):
    return mocker.patch("pod_store.episodes.requests.get")


# Autouse to prevent real shell commands being run during tests.
@pytest.fixture(autouse=True)
def mocked_subprocess_run(mocker):
    return mocker.patch("subprocess.run")


@pytest.fixture
def frozen_now(freezer):
    return datetime.utcnow()


@pytest.fixture
def podcast_episode_data(frozen_now):
    return {
        "aaa": {
            "id": "aaa",
            "download_path": os.path.join(TEST_PODCAST_DOWNLOAD_PATH, "0023-hello.mp3"),
            "episode_number": "0023",
            "title": "hello",
            "url": "http://foo.bar/aaa.mp3",
            "created_at": frozen_now.isoformat(),
            "updated_at": frozen_now.isoformat(),
            "downloaded_at": None,
        },
        "zzz": {
            "id": "zzz",
            "download_path": os.path.join(
                TEST_PODCAST_DOWNLOAD_PATH, "0011-goodbye.mp3"
            ),
            "episode_number": "0011",
            "title": "goodbye",
            "url": "http://foo.bar/zzz.mp3",
            "created_at": (frozen_now - timedelta(days=1)).isoformat(),
            "updated_at": (frozen_now - timedelta(days=1)).isoformat(),
            "downloaded_at": frozen_now.isoformat(),
        },
    }


@pytest.fixture
def store_podcasts_data(frozen_now, podcast_episode_data):
    return {
        "greetings": {
            "title": "greetings",
            "episode_downloads_path": "/foo/podcasts",
            "feed": "http://hello.world/rss",
            "episode_data": podcast_episode_data,
            "created_at": frozen_now.isoformat(),
            "updated_at": frozen_now.isoformat(),
        },
        "farewell": {
            "title": "farewell",
            "episode_downloads_path": "/bar/podcasts",
            "feed": "http://goodbye.world/rss",
            "episode_data": {},
            "created_at": (frozen_now - timedelta(days=1)).isoformat(),
            "updated_at": frozen_now.isoformat(),
        },
    }


@pytest.fixture
def store_file_handler():
    return StoreFileHandler(TEST_STORE_FILE_PATH)


@pytest.fixture
def store(store_file_handler):
    return Store(
        store_path=TEST_STORE_PATH,
        podcast_downloads_path=TEST_DOWNLOAD_PATH,
        file_handler=store_file_handler,
    )


@pytest.fixture
def start_with_no_store():
    shutil.rmtree(TEST_STORE_PATH)
