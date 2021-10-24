import json
import os
import shutil
from collections import namedtuple
from datetime import datetime, timedelta

import pytest

from pod_store.podcasts import Podcast
from pod_store.store import Store
from pod_store.store_file_handlers import UnencryptedStoreFileHandler
from tests import (
    TEST_AUDIO_FILE_PATH,
    TEST_PODCAST_DOWNLOADS_PATH,
    TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
    TEST_STORE_FILE_PATH,
    TEST_STORE_PATH,
)


# Autouse to establish fresh store data for every test.
@pytest.fixture(autouse=True)
def setup_test_store_data_and_downloads_path(request, store_data):
    def cleanup():
        if os.path.exists(TEST_STORE_PATH):
            shutil.rmtree(TEST_STORE_PATH)
        if os.path.exists(TEST_PODCAST_DOWNLOADS_PATH):
            shutil.rmtree(TEST_PODCAST_DOWNLOADS_PATH)

    cleanup()

    os.makedirs(TEST_STORE_PATH)
    os.makedirs(os.path.join(TEST_STORE_PATH, ".git"))  # register as "git enabled"
    os.makedirs(TEST_PODCAST_DOWNLOADS_PATH)
    with open(TEST_STORE_FILE_PATH, "w") as f:
        json.dump(store_data, f, indent=2)
    request.addfinalizer(cleanup)


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_feedparser_parse(mocker):
    return mocker.patch("pod_store.podcasts.feedparser.parse")


@pytest.fixture
def audio_file_content():
    with open(TEST_AUDIO_FILE_PATH, "rb") as f:
        return f.read()


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_requests_get(audio_file_content, mocker):
    stream_content = [audio_file_content]

    def iter_content(_):
        for chunk in stream_content:
            yield chunk

    fake_response = namedtuple("FakeResponse", "iter_content")
    resp = fake_response(iter_content=iter_content)
    return mocker.patch("pod_store.episodes.requests.get", return_value=resp)


# Autouse to prevent real shell commands being run during tests.
@pytest.fixture(autouse=True)
def mocked_subprocess_run(mocker):
    return mocker.patch("subprocess.run")


@pytest.fixture
def now(freezer):
    return datetime.utcnow()


@pytest.fixture
def yesterday(now):
    return now - timedelta(days=1)


@pytest.fixture
def podcast_episode_data(now, yesterday):
    return {
        "aaa": {
            "id": "aaa",
            "download_path": os.path.join(
                TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0023-hello.mp3"
            ),
            "episode_number": "0023",
            "title": "hello",
            "short_description": "hello world",
            "long_description": "hello world (longer description)",
            "url": "http://foo.bar/aaa.mp3",
            "tags": ["new"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "downloaded_at": None,
        },
        "zzz": {
            "id": "zzz",
            "download_path": os.path.join(
                TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0011-goodbye.mp3"
            ),
            "episode_number": "0011",
            "title": "goodbye",
            "short_description": "goodbye world",
            "long_description": "goodbye world (longer description)",
            "url": "http://foo.bar/zzz.mp3",
            "tags": ["foo"],
            "created_at": yesterday.isoformat(),
            "updated_at": yesterday.isoformat(),
            "downloaded_at": now.isoformat(),
        },
    }


@pytest.fixture
def store_data(now, yesterday, podcast_episode_data):
    return {
        "greetings": {
            "title": "greetings",
            "episode_downloads_path": os.path.join(
                TEST_PODCAST_DOWNLOADS_PATH, "greetings"
            ),
            "feed": "http://hello.world/rss",
            "tags": ["hello"],
            "episode_data": podcast_episode_data,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        "farewell": {
            "title": "farewell",
            "episode_downloads_path": os.path.join(
                TEST_PODCAST_DOWNLOADS_PATH, "farewell"
            ),
            "feed": "http://goodbye.world/rss",
            "tags": [],
            "episode_data": {
                "111": {
                    "id": "111",
                    "download_path": os.path.join(
                        TEST_PODCAST_DOWNLOADS_PATH, "farewell/0001-gone.mp3"
                    ),
                    "episode_number": "0001",
                    "title": "gone",
                    "short_description": "all gone",
                    "long_description": "all gone (longer description)",
                    "url": "http://foo.bar/111.mp3",
                    "tags": ["new", "bar"],
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "downloaded_at": None,
                },
            },
            "created_at": yesterday.isoformat(),
            "updated_at": now.isoformat(),
        },
        "other": {
            "title": "other",
            "episode_downloads_path": os.path.join(
                TEST_PODCAST_DOWNLOADS_PATH, "other"
            ),
            "feed": "http://other.thing/rss",
            "tags": [],
            "episode_data": {},
            "created_at": yesterday.isoformat(),
            "updated_at": now.isoformat(),
        },
    }


@pytest.fixture
def unencrypted_store_file_handler():
    return UnencryptedStoreFileHandler(TEST_STORE_FILE_PATH)


@pytest.fixture
def store(unencrypted_store_file_handler):
    return Store(
        store_path=TEST_STORE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
        file_handler=unencrypted_store_file_handler,
    )


@pytest.fixture
def podcast(now, podcast_episode_data):
    return Podcast(
        title="greetings",
        feed="http://hello.world/rss",
        tags=["greetings"],
        episode_downloads_path=TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
        created_at=now,
        updated_at=now,
        episode_data=podcast_episode_data,
    )


@pytest.fixture
def start_with_no_store():
    shutil.rmtree(TEST_STORE_PATH)
