import json
import os
import shutil

import pytest

from tests import TEST_DOWNLOAD_PATH, TEST_STORE_PATH

TEST_STORE_DATA = {
    "a/1.podcast.json": {
        "title": "a/1",
        "feed": "https://www.good.bye/rss",
        "created_at": "2021-01-01T01:01:01",
        "updated_at": "2021-01-01T01:01:01",
    },
    "b.podcast.json": {
        "title": "b",
        "feed": "https://www.foo.bar/rss",
        "created_at": "2021-01-02T01:01:01",
        "updated_at": "2021-01-02T01:01:01",
    },
    "b/abc.episode.json": {
        "id": "abc",
        "episode_number": "0092",
        "title": "hello",
        "url": "https://www.foo.bar/abc.mp3",
        "created_at": "2021-02-01T00:01:02",
        "updated_at": "2021-02-01T00:01:02",
        "downloaded_at": None,
    },
    "b/xyz.episode.json": {
        "id": "xyz",
        "episode_number": "0082",
        "title": "goodbye",
        "url": "https://www.foo.bar/xyz.mp3",
        "created_at": "2021-01-01T00:00:00",
        "updated_at": "2021-01-01T00:00:00",
        "downloaded_at": "2021-01-01T00:00:00",
    },
    "c/2.podcast.json": {
        "title": "c/2",
        "feed": "https://www.pod.cast/rss",
        "created_at": "2021-01-03T01:01:01",
        "updated_at": "2021-01-03T01:01:01",
    },
    "c/2/aaa.episode.json": {
        "id": "aaa",
        "episode_number": "0011",
        "title": "old news",
        "url": "https://www.pod.cast/aaa.mp3",
        "created_at": "2021-03-03T00:00:00",
        "updated_at": "2021-03-03T00:00:00",
        "downloaded_at": "2021-03-03T00:00:00",
    },
    "c/d/3.podcast.json": {
        "title": "c/d/3",
        "feed": "https://www.hello.world/rss",
        "created_at": "2021-01-04T01:01:01",
        "updated_at": "2021-01-04T01:01:01",
    },
}


# Autouse to establish fresh store data for every test.
@pytest.fixture(autouse=True)
def setup_test_store_data_and_downloads_path(request):
    def cleanup():
        if os.path.exists(TEST_STORE_PATH):
            shutil.rmtree(TEST_STORE_PATH)
        if os.path.exists(TEST_DOWNLOAD_PATH):
            shutil.rmtree(TEST_DOWNLOAD_PATH)

    cleanup()

    os.makedirs(TEST_STORE_PATH)
    os.makedirs(TEST_DOWNLOAD_PATH)
    for relative_path, file_data in TEST_STORE_DATA.items():
        file_path = os.path.join(TEST_STORE_PATH, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(file_data, f, indent=2)

    request.addfinalizer(cleanup)


# Use when you do NOT want the store to exist at the beginning of the test.
@pytest.fixture
def start_with_no_store():
    shutil.rmtree(TEST_STORE_PATH)


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_feedparser_parse(mocker):
    return mocker.patch("pod_store.podcast.feedparser.parse")


# Autouse to prevent real network calls during tests.
@pytest.fixture(autouse=True)
def mocked_requests_get(mocker):
    return mocker.patch("pod_store.episode.requests.get")


# Autouse to prevent real shell commands being run during tests.
@pytest.fixture(autouse=True)
def mocked_subprocess_run(mocker):
    return mocker.patch("subprocess.run")
