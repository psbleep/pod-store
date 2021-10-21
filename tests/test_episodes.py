import os
from collections import namedtuple

import pytest

from pod_store.episodes import Episode

from . import TEST_PODCAST_DOWNLOADS_PATH

TEST_EPISODE_DOWNLOAD_PATH = os.path.join(
    TEST_PODCAST_DOWNLOADS_PATH, "hello/0092-hello.mp3"
)


@pytest.fixture
def episode(now):
    return Episode(
        download_path=TEST_EPISODE_DOWNLOAD_PATH,
        id="abc",
        episode_number="0092",
        title="hello",
        summary="hello world",
        description="hello world (longer)",
        url="https://www.foo.bar/abc.mp3",
        tags=["new"],
        created_at=now,
        updated_at=now,
        downloaded_at=None,
    )


def test_episode_from_json_parses_datetimes(now):
    ts = now.isoformat()

    episode = Episode.from_json(
        download_path=TEST_EPISODE_DOWNLOAD_PATH,
        id="abc",
        episode_number="0092",
        title="hello",
        summary="hello world",
        description="hello world (longer)",
        url="https://www.foo.bar/abc.mp3",
        created_at=ts,
        updated_at=ts,
        downloaded_at=None,
    )

    assert episode.created_at == now
    assert episode.updated_at == now


def test_episode_download(now, mocked_requests_get, episode):
    def iter_content(_):
        for chunk in (b"hello ", b"world"):
            yield chunk

    fake_response = namedtuple("FakeResponse", "iter_content")
    resp = fake_response(iter_content=iter_content)
    mocked_requests_get.configure_mock(**{"return_value": resp})

    episode.download()
    mocked_requests_get.assert_called_with(episode.url, stream=True)

    assert episode.downloaded_at == now
    assert "new" not in episode.tags

    with open(episode.download_path, "rb") as f:
        assert f.read() == b"hello world"


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


def test_episode_to_json(now, episode):
    assert episode.to_json() == {
        "id": "abc",
        "download_path": TEST_EPISODE_DOWNLOAD_PATH,
        "episode_number": "0092",
        "title": "hello",
        "summary": "hello world",
        "description": "hello world (longer)",
        "url": "https://www.foo.bar/abc.mp3",
        "tags": ["new"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "downloaded_at": None,
    }
