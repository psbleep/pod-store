import os
from collections import namedtuple

import pytest

from pod_store.podcasts import Podcast

from . import TEST_PODCAST_EPISODE_DOWNLOADS_PATH


@pytest.fixture
def podcast(now, podcast_episode_data):
    return Podcast(
        title="hello",
        feed="http://hello.world/rss",
        tags=["greetings"],
        episode_downloads_path=TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
        created_at=now,
        updated_at=now,
        episode_data=podcast_episode_data,
    )


def test_podcast_from_json_parses_datetimes(now):
    podcast = Podcast.from_json(
        title="hello",
        feed="http://hello.world/rss",
        tags=["greetings"],
        episode_downloads_path=TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        episode_data={},
    )

    assert podcast.created_at == now
    assert podcast.updated_at == now


def test_podcast_has_new_episodes(podcast):
    assert podcast.has_new_episodes is True


def test_podcast_does_not_have_new_episodes(now, podcast):
    episode = podcast.episodes.get("aaa")
    episode.tags = []
    assert podcast.has_new_episodes is False


def test_podcast_refresh(mocked_feedparser_parse, now, podcast):
    now_parsed = (
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute,
        now.second,
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
                        "summary": "this is a short description",
                        "published_parsed": now_parsed,
                    },
                    {
                        "id": "https://www.foo.bar/aaa",
                        "itunes_episode": "0023",
                        "title": "hello-updated",
                        "summary": "hello world",
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

    assert podcast.updated_at == now
    assert podcast.episodes.ids == ["aaa", "ccc"]

    assert podcast.episodes.get("aaa").title == "hello-updated"

    new_episode = podcast.episodes.get("ccc")
    assert new_episode.download_path == os.path.join(
        TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0002-no-number-provided.mp3"
    )
    assert new_episode.episode_number == "0002"
    assert new_episode.summary == "this is a short descripti"
    assert new_episode.description == "this is a short description"


def test_podcast_tag(podcast):
    podcast.tag("hello")
    assert podcast.tags == ["greetings", "hello"]


def test_podcast_untag(podcast):
    podcast.untag("greetings")
    assert podcast.tags == []


def test_podcast_to_json(now, podcast_episode_data, podcast):
    assert podcast.to_json() == {
        "title": "hello",
        "feed": "http://hello.world/rss",
        "tags": ["greetings"],
        "episode_downloads_path": TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "episode_data": podcast_episode_data,
    }
