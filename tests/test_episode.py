import json
import os
from collections import namedtuple
from datetime import datetime

import pytest

from pod_store.episode import Episode
from pod_store.exc import EpisodeDoesNotExistError

from . import TEST_PODCAST_DOWNLOAD_PATH, TEST_STORE_PATH

TEST_EPISODE_FILE_PATH = os.path.join(TEST_STORE_PATH, "b/abc.episode.json")
TEST_EPISODE_DOWNLOAD_PATH = os.path.join(TEST_PODCAST_DOWNLOAD_PATH, "0092-hello.mp3")


@pytest.fixture
def episode():
    return Episode.from_store_file(
        store_file_path=TEST_EPISODE_FILE_PATH,
        base_download_path=TEST_PODCAST_DOWNLOAD_PATH,
    )


def test_from_store_file_loads_episode_data():
    episode = Episode.from_store_file(
        store_file_path=TEST_EPISODE_FILE_PATH,
        base_download_path=TEST_PODCAST_DOWNLOAD_PATH,
    )
    assert episode.id == "abc"
    assert episode.episode_number == "0092"
    assert episode.title == "hello"
    assert episode.url == "https://www.foo.bar/abc.mp3"
    assert episode.created_at == datetime(2021, 2, 1, 0, 1, 2)
    assert episode.updated_at == datetime(2021, 2, 1, 0, 1, 2)
    assert episode.downloaded_at is None


def test_episode_from_invalid_store_file_raises_exception():
    with pytest.raises(EpisodeDoesNotExistError):
        Episode.from_store_file("zzzzzz", base_download_path=TEST_PODCAST_DOWNLOAD_PATH)


def test_episode_sets_download_path(episode):
    assert episode._download_path == TEST_EPISODE_DOWNLOAD_PATH


def test_episode_download(mocked_requests_get, episode):
    def iter_content(_):
        for chunk in (b"hello ", b"world"):
            yield chunk

    response = namedtuple("FakeResponse", "iter_content")
    resp = response(iter_content=iter_content)
    mocked_requests_get.configure_mock(**{"return_value": resp})

    episode.download()
    mocked_requests_get.assert_called_with(episode.url, stream=True)

    with open(TEST_EPISODE_FILE_PATH) as f:
        assert json.load(f)["downloaded_at"] is not None

    with open(TEST_EPISODE_DOWNLOAD_PATH, "rb") as f:
        assert f.read() == b"hello world"


def test_episode_mark_as_downloaded(episode):
    episode.mark_as_downloaded()

    assert episode.downloaded_at is not None
    with open(TEST_EPISODE_FILE_PATH) as f:
        assert json.load(f)["downloaded_at"] is not None


def test_episode_update(episode):
    episode.update(title="updated", url="https://www.new.bar/")
    assert episode.title == "updated"
    assert episode.url == "https://www.new.bar/"


def test_episode_to_json(episode):
    assert episode.to_json() == {
        "id": "abc",
        "episode_number": "0092",
        "title": "hello",
        "url": "https://www.foo.bar/abc.mp3",
        "created_at": "2021-02-01T00:01:02",
        "updated_at": "2021-02-01T00:01:02",
        "downloaded_at": None,
    }


def test_episode_save(episode):
    episode.title = "new title"
    episode.save()

    with open(TEST_EPISODE_FILE_PATH) as f:
        assert json.load(f)["title"] == "new title"
