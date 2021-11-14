import os

import music_tag
import pytest

from pod_store.episodes import Episode

from . import TEST_PODCAST_EPISODE_DOWNLOADS_PATH

TEST_EPISODE_DOWNLOAD_PATH = os.path.join(
    TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0092-hello.mp3"
)


def test_episode_from_json_parses_datetimes(now, podcast):
    ts = now.isoformat()

    episode = Episode.from_json(
        podcast=podcast,
        id="abc",
        episode_number="0092",
        title="hello",
        short_description="hello world",
        long_description="hello world (longer description)",
        url="https://www.foo.bar/abc.mp3",
        created_at=ts,
        updated_at=ts,
        downloaded_at=None,
    )

    assert episode.created_at == now
    assert episode.updated_at == now


def test_episode_download_path_is_correct_path_for_filetype_without_invalid_characters(
    now, podcast
):
    episode = Episode(
        podcast=podcast,
        id="bbb",
        episode_number=981,
        title="foo/bar: the fin?al[ RE:^'ckONing",
        short_description="foo",
        long_description="foo (longer description)",
        url="http://foo.bar/bbb.ogg?jd289ds89xchw",
        created_at=now,
        updated_at=now,
    )

    assert episode.download_path == os.path.join(
        TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0981-foo-bar-the-fin-al-re-ckoning.ogg"
    )


def test_episode_is_new(episode):
    episode.tags = ["new"]
    assert episode.is_new is True


def test_episode_is_not_new(episode):
    episode.tags = []
    assert episode.is_new is False


def test_episode_download(now, audio_file_content, episode):
    with episode.download() as download:
        list(download)

    assert episode.downloaded_at == now
    assert "new" not in episode.tags

    metadata = music_tag.load_file(episode.download_path)
    assert metadata["artist"].value == "greetings"
    assert metadata["album"].value == "greetings"
    assert metadata["album_artist"].value == "greetings"
    assert metadata["title"].value == "hello"
    assert metadata["track_title"].value == "hello"
    assert metadata["genre"].value == "Podcast"
    assert metadata["track_number"].value == 23
    assert metadata["year"].value == now.year

    with open(episode.download_path, "rb") as f:
        assert f.read()[-1000:] == audio_file_content[-1000:]


def test_episode_download_does_not_run_clean_up_if_errors_encoutnered(
    mocked_requests_get, episode
):
    mocked_requests_get.configure_mock(**{"side_effect": TypeError})
    with pytest.raises(TypeError):
        with episode.download() as download:
            list(download)

    assert episode.downloaded_at is None
    assert "new" in episode.tags


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
        "id": "aaa",
        "episode_number": 23,
        "title": "hello",
        "short_description": "hello world",
        "long_description": "hello world (longer description)",
        "url": "https://www.foo.bar/aaa.mp3",
        "tags": ["new"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "downloaded_at": None,
    }
