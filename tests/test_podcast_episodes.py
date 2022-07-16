import pytest

from pod_store.exc import EpisodeDoesNotExistError
from pod_store.podcasts import PodcastEpisodes


@pytest.fixture
def podcast_episodes(podcast, podcast_episode_data):
    return PodcastEpisodes(
        podcast=podcast,
        episode_data=podcast_episode_data,
    )


def test_podcast_episodes_add_episode_to_store(now, podcast_episodes):
    podcast_episodes.add(
        id="xyz",
        episode_number="000",
        title="new",
        short_description="short description",
        long_description="long description",
        url="https://new.time/000-new.mp3",
        created_at=now,
        updated_at=now,
    )

    assert podcast_episodes.get("xyz").title == "new"


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


def test_podcast_episodes_list_sorts_by_episode_number(podcast_episodes):
    ep1, ep2 = podcast_episodes.list()
    assert ep1.id == "aaa"
    assert ep2.id == "zzz"


def test_podcast_episodes_to_json(podcast_episodes, podcast_episode_data):
    assert podcast_episodes.to_json() == podcast_episode_data
