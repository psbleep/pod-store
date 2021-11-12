import pytest

from pod_store.commands.filtering import EpisodeFilter, PodcastFilter
from pod_store.exc import NoEpisodesFoundError, NoPodcastsFoundError


def _get_episode_ids(episodes):
    return [e.id for e in episodes]


def _get_podcast_titles(podcasts):
    return [p.title for p in podcasts]


def test_episode_filter_all_episodes(store):
    filter = EpisodeFilter(
        store=store,
    )
    assert _get_episode_ids(filter.items) == ["111", "222", "aaa", "zzz"]


def test_episode_filter_new_episodes(store):
    filter = EpisodeFilter(store=store, new_episodes=True)
    assert _get_episode_ids(filter.items) == ["111", "aaa"]


def test_episode_filter_with_tags(store):
    filter = EpisodeFilter(store=store, foo=True)
    assert _get_episode_ids(filter.items) == ["222", "zzz"]


def test_episode_filter_without_tags(store):
    filter = EpisodeFilter(store=store, foo=False)
    assert _get_episode_ids(filter.items) == ["111", "aaa"]


def test_episode_filter_for_podcast(store):
    filter = EpisodeFilter(store=store, podcast_title="greetings")
    assert _get_episode_ids(filter.items) == ["aaa", "zzz"]


def test_episode_filter_for_podcasts_with_extra_podcast_filters(store):
    filter = EpisodeFilter(store=store, podcast_filters={"hello": True})
    assert _get_episode_ids(filter.items) == ["aaa", "zzz"]


def test_episode_filter_raises_exception_if_no_episodes_found(store):
    filter = EpisodeFilter(store=store, tags=["whoooo"])
    with pytest.raises(NoEpisodesFoundError):
        filter.items


def test_podcast_filter_all_podcasts(store):
    filter = PodcastFilter(store=store)
    assert _get_podcast_titles(filter.items) == ["farewell", "other", "greetings"]


def test_podcast_filter_with_new_episodes(store):
    filter = PodcastFilter(store=store, new_episodes=True)
    assert _get_podcast_titles(filter.items) == ["farewell", "greetings"]


def test_podcast_filter_list_podcasts_with_tags(store):
    filter = PodcastFilter(store=store, hello=True)
    assert _get_podcast_titles(filter.items) == ["greetings"]


def test_podcast_filter_list_podcasts_without_tags(store):
    filter = PodcastFilter(store=store, hello=False)
    assert _get_podcast_titles(filter.items) == ["farewell", "other"]


def test_podcast_filter_single_podcast(store):
    filter = PodcastFilter(store=store, new_episodes=True, podcast_title="farewell")
    assert _get_podcast_titles(filter.items) == ["farewell"]


def test_podcast_filter_raises_exception_if_no_podcasts_found(store):
    filter = PodcastFilter(store=store, tags=["whoooo"])
    with pytest.raises(NoPodcastsFoundError):
        filter.items
