import json
import os
from collections import namedtuple

import pytest

from pod_store.exc import PodcastDoesNotExistError
from pod_store.podcast import Podcast

from . import TEST_DOWNLOAD_PATH, TEST_PODCAST_FILE_PATH, TEST_STORE_PATH


def _get_episode_titles(episodes):
    return [e.title for e in episodes]


@pytest.fixture
def podcast():
    return Podcast.from_store_file(TEST_PODCAST_FILE_PATH)


def test_podcast_data_is_loaded_from_file():
    podcast = Podcast.from_store_file(TEST_PODCAST_FILE_PATH)
    assert podcast.title == "b"
    assert podcast.feed == "https://www.foo.bar/rss"

    assert podcast._downloads_path == os.path.join(TEST_DOWNLOAD_PATH, "b")


def test_podcast_from_invalid_store_file_raises_exception():
    with pytest.raises(PodcastDoesNotExistError):
        Podcast.from_store_file("zzzzzzzzzzzz")


def test_has_new_episodes(podcast):
    assert podcast.has_new_episodes is True


def test_has_new_episodes_no_new_episodes(podcast):
    os.remove(os.path.join(podcast.store_episodes_path, "abc.episode.json"))
    assert podcast.has_new_episodes is False


def test_podcast_list_episodes(podcast):
    assert _get_episode_titles(podcast.list_episodes()) == ["hello", "goodbye"]


def test_podcast_list_episodes_podcast_episodes_directory_does_not_exist_yet():
    store_file_path = os.path.join(TEST_STORE_PATH, "a/1.podcast.json")
    podcast = Podcast.from_store_file(store_file_path)
    assert podcast.list_episodes() == []


def test_podcast_list_new_episodes(podcast):
    assert _get_episode_titles(podcast.list_new_episodes()) == ["hello"]


def test_podcast_search_episodes(podcast):
    assert _get_episode_titles(podcast.search_episodes("oo")) == ["goodbye"]


def test_podcast_refresh(mocked_feedparser_parse, podcast):
    parsed_feed = namedtuple("parsed", ["entries"])
    mocked_feedparser_parse.configure_mock(
        **{
            "return_value": parsed_feed(
                [
                    {
                        "id": "https://www.foo.bar/abc",
                        "itunes_episode": "92",
                        "title": "hello-updated",
                        "links": [
                            {
                                "href": "https://www.foo.bar/abc.mp3",
                                "type": "audio/mpeg",
                            }
                        ],
                        "published_parsed": (2021, 2, 1, 0, 1, 2),
                        "updated_parsed": (2021, 2, 1, 0, 1, 2),
                    },
                    {
                        "id": "ccc",
                        "title": "no-number-provided",
                        "links": [
                            {"href": "https://www.foo.bar/ccc.mp3", "type": "audio/mp3"}
                        ],
                        "published_parsed": (2021, 1, 1, 1, 1, 1, 1, 1, 1, 1),
                    },
                    {
                        "id": "zzz",
                        "title": "brand-new 93",
                        "links": [
                            {
                                "href": "https://www.foo.bar/zzz.mp3",
                                "type": "audio/mpeg",
                            }
                        ],
                        "published_parsed": (2021, 3, 1, 0, 1, 2),
                        "updated_parsed": (2021, 3, 1, 0, 1, 2),
                        "non": "sense",
                    },
                ]
            )
        }
    )

    episode_path = os.path.join(podcast.store_episodes_path, "abc.episode.json")
    removed_episode_path = os.path.join(podcast.store_episodes_path, "xyz.episode.json")
    new_episode_path1 = os.path.join(podcast.store_episodes_path, "ccc.episode.json")
    new_episode_path2 = os.path.join(podcast.store_episodes_path, "zzz.episode.json")

    assert os.path.exists(removed_episode_path)

    podcast.refresh()

    with open(episode_path) as f:
        assert json.load(f) == {
            "id": "abc",
            "episode_number": "0092",
            "title": "hello-updated",
            "url": "https://www.foo.bar/abc.mp3",
            "created_at": "2021-02-01T00:01:02",
            "updated_at": "2021-02-01T00:01:02",
            "downloaded_at": None,
        }

    with open(new_episode_path1) as f:
        assert json.load(f) == {
            "id": "ccc",
            "episode_number": "0002",
            "title": "no-number-provided",
            "url": "https://www.foo.bar/ccc.mp3",
            "created_at": "2021-01-01T01:01:01",
            "updated_at": "2021-01-01T01:01:01",
            "downloaded_at": None,
        }

    with open(new_episode_path2) as f:
        assert json.load(f) == {
            "id": "zzz",
            "episode_number": "0093",
            "title": "brand-new 93",
            "url": "https://www.foo.bar/zzz.mp3",
            "created_at": "2021-03-01T00:01:02",
            "updated_at": "2021-03-01T00:01:02",
            "downloaded_at": None,
        }

    assert not os.path.exists(removed_episode_path)


def test_podcast_to_json(podcast):
    assert podcast.to_json() == {
        "title": "b",
        "feed": "https://www.foo.bar/rss",
        "created_at": "2021-01-02T01:01:01",
        "updated_at": "2021-01-02T01:01:01",
    }


def test_save_podcast(podcast):
    podcast.feed = "https://www.pod.cast/rss/new"
    podcast.save()
    with open(TEST_PODCAST_FILE_PATH) as f:
        assert json.load(f)["feed"] == "https://www.pod.cast/rss/new"
