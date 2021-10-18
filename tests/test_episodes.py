import os
from collections import namedtuple

import pytest

from pod_store.episodes import Episode

from . import TEST_PODCAST_DOWNLOADS_PATH

TEST_EPISODE_DOWNLOAD_PATH = os.path.join(
    TEST_PODCAST_DOWNLOADS_PATH, "hello/0092-hello.mp3"
)


@pytest.fixture
def episode(frozen_now):
    return Episode(
        download_path=TEST_EPISODE_DOWNLOAD_PATH,
        id="abc",
        episode_number="0092",
        title="hello",
        url="https://www.foo.bar/abc.mp3",
        tags=["new"],
        created_at=frozen_now,
        updated_at=frozen_now,
        downloaded_at=None,
    )


def test_episode_from_json_parses_datetimes(frozen_now):
    ts = frozen_now.isoformat()

    episode = Episode.from_json(
        download_path=TEST_EPISODE_DOWNLOAD_PATH,
        id="abc",
        episode_number="0092",
        title="hello",
        url="https://www.foo.bar/abc.mp3",
        created_at=ts,
        updated_at=ts,
        downloaded_at=None,
    )

    assert episode.created_at == frozen_now
    assert episode.updated_at == frozen_now


def test_episode_string_not_downloaded_yet(episode):
    assert str(episode) == "[0092] hello "


def test_episode_string_has_been_downloaded(frozen_now, episode):
    episode.downloaded_at = frozen_now
    assert str(episode) == "[0092] hello [X]"


def test_episode_download(frozen_now, mocked_requests_get, episode):
    def iter_content(_):
        for chunk in (b"hello ", b"world"):
            yield chunk

    response = namedtuple("FakeResponse", "iter_content")
    resp = response(iter_content=iter_content)
    mocked_requests_get.configure_mock(**{"return_value": resp})

    episode.download()
    mocked_requests_get.assert_called_with(episode.url, stream=True)

    assert episode.downloaded_at == frozen_now

    with open(episode.download_path, "rb") as f:
        assert f.read() == b"hello world"


def test_episode_mark_as_downloaded(frozen_now, episode):
    episode.mark_as_downloaded()
    assert episode.downloaded_at == frozen_now


def test_episode_update(episode):
    episode.update(title="updated", url="https://www.new.bar/")
    assert episode.title == "updated"
    assert episode.url == "https://www.new.bar/"


def test_episide_tag(episode):
    episode.tag("foobar")
    assert episode.tags == ["new", "foobar"]


def test_episode_untag(episode):
    episode.untag("new")
    assert episode.tags == []


def test_episode_to_json(frozen_now, episode):
    assert episode.to_json() == {
        "id": "abc",
        "download_path": TEST_EPISODE_DOWNLOAD_PATH,
        "episode_number": "0092",
        "title": "hello",
        "url": "https://www.foo.bar/abc.mp3",
        "tags": ["new"],
        "created_at": frozen_now.isoformat(),
        "updated_at": frozen_now.isoformat(),
        "downloaded_at": None,
    }
