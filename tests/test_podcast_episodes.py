import os

import pytest

from pod_store.exc import EpisodeDoesNotExistError
from pod_store.podcasts import PodcastEpisodes

from . import TEST_PODCAST_DOWNLOAD_PATH


@pytest.fixture
def podcast_episodes(podcast_episode_data):
    return PodcastEpisodes(
        episode_downloads_path=TEST_PODCAST_DOWNLOAD_PATH,
        episode_data=podcast_episode_data,
    )


def test_podcast_episodes_add_episode_sets_download_path_from_episode_number_and_title(
    frozen_now, podcast_episodes
):
    episode = podcast_episodes.add(
        id="bbb",
        episode_number="0981",
        title="foo",
        url="http://foo.bar/bbb.mp3",
        created_at=frozen_now,
        updated_at=frozen_now,
    )

    assert episode.download_path == os.path.join(
        TEST_PODCAST_DOWNLOAD_PATH, "0981-foo.mp3"
    )

    assert podcast_episodes._episodes["bbb"] == episode


def test_podcast_episodes_delete_episode(podcast_episodes):
    podcast_episodes.delete("zzz")
    assert "zzz" not in podcast_episodes._episodes


def test_podcast_episodes_get_episode(podcast_episodes):
    assert podcast_episodes.get("aaa").title == "hello"


def test_podcast_episodes_get_episode_raises_exception_if_not_found(podcast_episodes):
    with pytest.raises(EpisodeDoesNotExistError):
        podcast_episodes.get("xxx")


def test_podcast_episodes_get_episode_allow_empty_returns_none_if_not_found(
    podcast_episodes,
):
    assert podcast_episodes.get("fooooo", allow_empty=True) is None


def test_podcast_episodes_list_sorts_by_created_time(podcast_episodes):
    ep1, ep2 = podcast_episodes.list()
    assert ep1.id == "aaa"
    assert ep2.id == "zzz"


def test_podcast_episodes_list_filter(podcast_episodes):
    episodes = podcast_episodes.list(downloaded_at=None)
    assert len(episodes) == 1
    assert episodes[0].id == "aaa"


def test_podcast_episodes_to_json(podcast_episodes, podcast_episode_data):
    assert podcast_episodes.to_json() == podcast_episode_data
