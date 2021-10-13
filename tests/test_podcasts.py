import os
from collections import namedtuple

import pytest

from pod_store.podcasts import Podcast

from . import TEST_DOWNLOAD_PATH

TEST_PODCAST_DOWNLOAD_PATH = os.path.join(TEST_DOWNLOAD_PATH, "hello")


@pytest.fixture
def podcast(frozen_now, podcast_episode_data):
    return Podcast(
        title="hello",
        feed="http://hello.world/rss",
        episode_downloads_path=TEST_PODCAST_DOWNLOAD_PATH,
        created_at=frozen_now,
        updated_at=frozen_now,
        episode_data=podcast_episode_data,
    )


def test_podcast_from_json_parses_datetimes(frozen_now):
    podcast = Podcast.from_json(
        title="hello",
        feed="http://hello.world/rss",
        episode_downloads_path=TEST_PODCAST_DOWNLOAD_PATH,
        created_at=frozen_now.isoformat(),
        updated_at=frozen_now.isoformat(),
        episode_data={},
    )

    assert podcast.created_at == frozen_now
    assert podcast.updated_at == frozen_now


def test_podcast_has_new_episodes(podcast):
    assert podcast.has_new_episodes is True


def test_podcast_does_not_have_new_episodes(frozen_now, podcast):
    episode = podcast.episodes.get("aaa")
    episode.downloaded_at = frozen_now
    assert podcast.has_new_episodes is False


def test_podcast_refresh(frozen_now, mocked_feedparser_parse, podcast):
    now_parsed = (
        frozen_now.year,
        frozen_now.month,
        frozen_now.day,
        frozen_now.hour,
        frozen_now.minute,
        frozen_now.second,
    )

    parsed_feed = namedtuple("parsed", ["entries"])
    mocked_feedparser_parse.configure_mock(
        **{
            "return_value": parsed_feed(
                [
                    {
                        "id": "ccc",
                        "title": "no-number-provided",
                        "links": [
                            {"href": "https://www.foo.bar/ccc.mp3", "type": "audio/mp3"}
                        ],
                        "published_parsed": now_parsed,
                    },
                    {
                        "id": "https://www.foo.bar/aaa",
                        "itunes_episode": "0023",
                        "title": "hello-updated",
                        "links": [
                            {
                                "href": "http://www.foo.bar/aaa.mp3",
                                "type": "audio/mpeg",
                            }
                        ],
                        "published_parsed": now_parsed,
                        "updated_parsed": now_parsed,
                    },
                ]
            )
        }
    )

    podcast.refresh()

    assert podcast.updated_at == frozen_now

    assert "zzz" not in podcast.episodes._episodes

    assert podcast.episodes.get("aaa").title == "hello-updated"

    new_episode = podcast.episodes.get("ccc")
    assert new_episode.download_path == os.path.join(
        TEST_PODCAST_DOWNLOAD_PATH, "0002-no-number-provided.mp3"
    )
    assert new_episode.episode_number == "0002"


def test_podcast_to_json(frozen_now, podcast_episode_data, podcast):
    assert podcast.to_json() == {
        "title": "hello",
        "feed": "http://hello.world/rss",
        "episode_downloads_path": TEST_PODCAST_DOWNLOAD_PATH,
        "created_at": frozen_now.isoformat(),
        "updated_at": frozen_now.isoformat(),
        "episode_data": podcast_episode_data,
    }
