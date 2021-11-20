import pytest

from pod_store.commands.filtering import EpisodeFilter, Filter, PodcastFilter
from pod_store.exc import (
    AmbiguousEpisodeError,
    NoEpisodesFoundError,
    NoPodcastsFoundError,
)


def _get_episode_ids(episodes):
    return [e.id for e in episodes]


def _get_podcast_titles(podcasts):
    return [p.title for p in podcasts]


def test_filter_from_command_arguments_podcast_filter(store):
    filter = Filter.from_command_arguments(store=store)
    assert isinstance(filter, PodcastFilter)


def test_filter_from_command_arguments_episode_filter(store):
    filter = Filter.from_command_arguments(store=store, filter_for_episodes=True)
    assert isinstance(filter, EpisodeFilter)


def test_filter_from_command_arguments_filters_for_episodes_if_podcast_title_is_present(
    store,
):
    filter = Filter.from_command_arguments(store=store, podcast_title="greetings")
    assert isinstance(filter, EpisodeFilter)


def test_filter_from_command_arguments_filter_for_single_episode(
    store,
):
    filter = Filter.from_command_arguments(
        store=store, podcast_title="greetings", episode_number=23
    )

    # When a user specifies a single episode, it should be returned whether or not it
    # is a new episode (even if the user has not specified whether to filter for new
    # episodes or not).
    assert filter.new_episodes is False
    assert filter.filters == {"episode_number": 23}


def test_filter_from_command_arguments_accepts_with_tags(store):
    filter = Filter.from_command_arguments(
        store=store, tagged=["foo"], untagged=["bar"]
    )
    assert filter.filters == {"foo": True, "bar": False}


def test_filter_from_command_arguments_accepts_extra_podcast_tags(store):
    filter = Filter.from_command_arguments(
        store=store, podcasts_tagged=["hello"], podcasts_untagged=["bar"]
    )
    assert filter.filters == {}  # Extra podcast tags are not applied to main filters.
    assert filter.extra_podcast_filters == {"hello": True, "bar": False}


def test_filter_from_command_arguments_single_episode_without_podcast_raises_error(
    store,
):
    with pytest.raises(AmbiguousEpisodeError):
        Filter.from_command_arguments(store=store, episode_number=23)


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


def test_episode_filter_for_individual_episode(store):
    filter = EpisodeFilter(store=store, podcast_title="greetings", episode_number=23)
    assert _get_episode_ids(filter.items) == ["aaa"]


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


def test_podcast_filter_podcasts_with_tags(store):
    filter = PodcastFilter(store=store, hello=True)
    assert _get_podcast_titles(filter.items) == ["greetings"]


def test_podcast_filter_podcasts_without_tags(store):
    filter = PodcastFilter(store=store, hello=False)
    assert _get_podcast_titles(filter.items) == ["farewell", "other"]


def test_podcast_filter_single_podcast(store):
    filter = PodcastFilter(store=store, new_episodes=True, podcast_title="farewell")
    assert _get_podcast_titles(filter.items) == ["farewell"]


def test_podcast_filter_raises_exception_if_no_podcasts_found(store):
    filter = PodcastFilter(store=store, tags=["whoooo"])
    with pytest.raises(NoPodcastsFoundError):
        filter.items
