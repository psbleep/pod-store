import json
import os
import shutil
from collections import namedtuple
from datetime import datetime, timedelta

import pytest

from pod_store.commands.tagging import Tagger
from pod_store.episodes import Episode
from pod_store.podcasts import Podcast
from pod_store.store import Store
from pod_store.store_file_handlers import UnencryptedStoreFileHandler
from tests import (
    TEST_AUDIO_FILE_PATH,
    TEST_PODCAST_DOWNLOADS_PATH,
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
def mocked_command_helpers_click_secho(mocker):
    return mocker.patch("pod_store.commands.helpers.click.secho")


@pytest.fixture
def audio_file_content():
    with open(TEST_AUDIO_FILE_PATH, "rb") as f:
        return f.read()


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_requests_get(audio_file_content, mocker):
    # Provide fake data for both `iter_content`  attribute (episode download tests)
    # and `content` attribute (podcast RSS refresh tests).
    fake_response = namedtuple("FakeResponse", ["iter_content", "content", "headers"])
    stream_content = [audio_file_content]

    def iter_content(_):
        for chunk in stream_content:
            yield chunk

    resp = fake_response(
        iter_content=iter_content, content=b"", headers={"content-length": "2000"}
    )
    return mocker.patch("requests.get", return_value=resp)


# Autouse to prevent real shell commands being run during tests.
@pytest.fixture(autouse=True)
def mocked_subprocess_run(mocker):
    return mocker.patch("subprocess.run")


@pytest.fixture
def now(freezer):
    return datetime.utcnow()


@pytest.fixture
def now_formatted(now):
    return now.isoformat()


@pytest.fixture
def yesterday(now):
    return now - timedelta(days=1)


@pytest.fixture
def yesterday_formatted(yesterday):
    return yesterday.isoformat()


@pytest.fixture
def podcast_episode_data(now, yesterday):
    return {
        "aaa": {
            "id": "aaa",
            "episode_number": 23,
            "title": "hello",
            "short_description": "hello world",
            "long_description": "hello world (longer description)",
            "url": "http://foo.bar/aaa.mp3",
            "tags": ["new"],
            "created_at": yesterday.isoformat(),
            "updated_at": yesterday.isoformat(),
            "downloaded_at": None,
        },
        "zzz": {
            "id": "zzz",
            "episode_number": 11,
            "title": "goodbye",
            "short_description": "goodbye world",
            "long_description": "goodbye world (longer description)",
            "url": "http://foo.bar/zzz.mp3",
            "tags": ["foo"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "downloaded_at": now.isoformat(),
        },
    }


@pytest.fixture
def other_podcast_episode_data(now):
    return {
        "111": {
            "id": "111",
            "episode_number": 1,
            "title": "gone",
            "short_description": "all gone",
            "long_description": "all gone (longer description)",
            "url": "http://foo.bar/111.mp3",
            "tags": ["new", "bar"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "downloaded_at": None,
        },
        "222": {
            "id": "222",
            "episode_number": 2,
            "title": "not forgotten",
            "short_description": "never forgotten",
            "long_description": "never forgotten (longer description)",
            "url": "http://foo.bar/222.mp3",
            "tags": ["foo", "bar"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "downloaded_at": None,
        },
    }


@pytest.fixture
def store_data(now, yesterday, podcast_episode_data, other_podcast_episode_data):
    return {
        "greetings": {
            "title": "greetings",
            "feed": "http://hello.world/rss",
            "tags": ["hello"],
            "episode_data": podcast_episode_data,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        "farewell": {
            "title": "farewell",
            "feed": "http://goodbye.world/rss",
            "tags": [],
            "episode_data": other_podcast_episode_data,
            "created_at": yesterday.isoformat(),
            "updated_at": now.isoformat(),
        },
        "other": {
            "title": "other",
            "feed": "http://other.thing/rss",
            "tags": ["inactive"],
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
        file_handler=unencrypted_store_file_handler,
    )


@pytest.fixture
def podcast(now, podcast_episode_data):
    return Podcast(
        title="greetings",
        feed="http://hello.world/rss",
        tags=["greetings"],
        created_at=now,
        updated_at=now,
        episode_data=podcast_episode_data,
    )


@pytest.fixture
def episode(now, podcast):
    return Episode(
        podcast=podcast,
        id="aaa",
        episode_number=23,
        title="hello",
        short_description="hello world",
        long_description="hello world (longer description)",
        url="https://www.foo.bar/aaa.mp3",
        tags=["new"],
        created_at=now,
        updated_at=now,
        downloaded_at=None,
    )


@pytest.fixture
def tagger():
    return Tagger(
        action="choose",
        performing_action="choosing",
        performed_action="chosen",
    )


@pytest.fixture
def start_with_no_store():
    shutil.rmtree(TEST_STORE_PATH)


@pytest.fixture
def mocked_git_clone_with_empty_repo(mocker):
    return mocker.patch(
        "pod_store.store.run_shell_command",
        side_effect=lambda _: os.makedirs(TEST_STORE_PATH),
    )


@pytest.fixture
def mocked_git_clone_with_store_file(mocker):
    def _create_store_file(*args, **kwargs):
        os.makedirs(TEST_STORE_PATH)
        with open(TEST_STORE_FILE_PATH, "w") as f:
            f.write("")

    return mocker.patch(
        "pod_store.store.run_shell_command", side_effect=_create_store_file
    )
