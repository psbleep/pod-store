import os

import pytest

from pod_store.exc import EpisodeDoesNotExistError, NoEpisodesFoundError
from pod_store.podcasts import PodcastEpisodes

from . import TEST_PODCAST_EPISODE_DOWNLOADS_PATH


@pytest.fixture
def podcast_episodes(podcast, podcast_episode_data):
    return PodcastEpisodes(
        podcast=podcast,
        episode_data=podcast_episode_data,
    )


def test_podcast_episodes_add_sets_valid_download_path_from_episode_num_and_title(
    now, podcast_episodes
):
    episode = podcast_episodes.add(
        id="bbb",
        episode_number="0981",
        title="foo/bar: the fin?al[ RE:^ckONing",
        short_description="foo",
        long_description="foo (longer description)",
        url="http://foo.bar/bbb.mp3",
        created_at=now,
        updated_at=now,
    )

    assert episode.download_path == os.path.join(
        TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0981-foo-bar--the-fin-al--re--ckoning.mp3"
    )

    assert podcast_episodes.get("bbb").episode_number == "0981"


def test_podcast_episodes_delete_episode(podcast_episodes):
    podcast_episodes.delete("zzz")
    assert "zzz" not in podcast_episodes.ids


def test_podcast_episodes_delete_episode_not_found(podcast_episodes):
    with pytest.raises(EpisodeDoesNotExistError):
        podcast_episodes.delete("xubu")


def test_podcast_episodes_get_episode(podcast_episodes):
    assert podcast_episodes.get("aaa").title == "hello"


def test_podcast_episodes_get_episode_raises_exception_if_not_found(podcast_episodes):
    with pytest.raises(EpisodeDoesNotExistError):
        podcast_episodes.get("xxx")


def test_podcast_episodes_get_episode_allow_empty_returns_none_if_not_found(
    podcast_episodes,
):
    assert podcast_episodes.get("fooooo", allow_empty=True) is None


def test_podcast_episodes_list_sorts_episodes_by_created_time(podcast_episodes):
    ep1, ep2 = podcast_episodes.list()
    assert ep1.id == "aaa"
    assert ep2.id == "zzz"


def test_podcast_episodes_list_filters_episodes(podcast_episodes):
    episodes = podcast_episodes.list(downloaded_at=None)
    assert len(episodes) == 1
    assert episodes[0].id == "aaa"


def test_podcast_episodes_list_filters_episodes_by_presence_of_tag(podcast_episodes):
    ep = podcast_episodes.get("aaa")
    ep.tags = ["foobar"]

    episodes = podcast_episodes.list(foobar=True)
    assert len(episodes) == 1
    assert episodes[0].id == "aaa"


def test_podcast_episoes_list_filter_episodes_by_absence_of_tag(podcast_episodes):
    episodes = podcast_episodes.list(new=False)
    assert len(episodes) == 1
    assert episodes[0].id == "zzz"


def test_podcsat_episode_list_filter_raises_exception_if_filter_is_not_attribute_or_tag(
    podcast_episodes,
):
    with pytest.raises(AttributeError):
        podcast_episodes.list(zozozozo="hello")


def test_podcast_episodes_list_no_episodes_found_raises_exception_if_not_allowed(
    podcast_episodes,
):
    with pytest.raises(NoEpisodesFoundError):
        podcast_episodes.list(allow_empty=False, id="abcdefg")


def test_podcast_episodes_list_no_episodes_found_returns_empty_list_if_allowed(
    podcast_episodes,
):
    assert podcast_episodes.list(allow_empty=True, id="abcdefg") == []


def test_podcast_episodes_to_json(podcast_episodes, podcast_episode_data):
    assert podcast_episodes.to_json() == podcast_episode_data
