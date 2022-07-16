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
    pod_store_filter = Filter.from_command_arguments(store=store)
    assert isinstance(pod_store_filter, PodcastFilter)


def test_filter_from_command_arguments_episode_filter(store):
    pod_store_filter = Filter.from_command_arguments(
        store=store, filter_for_episodes=True
    )
    assert isinstance(pod_store_filter, EpisodeFilter)


def test_filter_from_command_arguments_filters_for_episodes_if_podcast_title_is_present(
    store,
):
    pod_store_filter = Filter.from_command_arguments(
        store=store, podcast_title="greetings"
    )
    assert isinstance(pod_store_filter, EpisodeFilter)


def test_filter_from_command_arguments_filter_for_single_episode(
    store,
):
    pod_store_filter = Filter.from_command_arguments(
        store=store, podcast_title="greetings", episode_number=23
    )

    # When a user specifies a single episode, it should be returned whether or not it
    # is a new episode (even if the user has not specified whether to filter for new
    # episodes or not).
    assert pod_store_filter.new_episodes is False
    assert pod_store_filter.filters == {"episode_number": 23}


def test_filter_from_command_arguments_accepts_with_tags(store):
    pod_store_filter = Filter.from_command_arguments(
        store=store, tagged=["foo"], untagged=["bar"]
    )
    assert pod_store_filter.filters == {"foo": True, "bar": False}


def test_filter_from_command_arguments_accepts_extra_podcast_tags(store):
    pod_store_filter = Filter.from_command_arguments(
        store=store, podcasts_tagged=["hello"], podcasts_untagged=["bar"]
    )
    assert (
        pod_store_filter.filters == {}
    )  # Extra podcast tags are not applied to main filters.
    assert pod_store_filter.extra_podcast_filters == {"hello": True, "bar": False}


def test_filter_from_command_arguments_single_episode_without_podcast_raises_error(
    store,
):
    with pytest.raises(AmbiguousEpisodeError):
        Filter.from_command_arguments(store=store, episode_number=23)


def test_episode_filter_all_episodes(store):
    pod_store_filter = EpisodeFilter(
        store=store,
    )
    assert _get_episode_ids(pod_store_filter.items) == ["222", "111", "aaa", "zzz"]


def test_episode_filter_new_episodes(store):
    pod_store_filter = EpisodeFilter(store=store, new_episodes=True)
    assert _get_episode_ids(pod_store_filter.items) == ["111", "aaa"]


def test_episode_filter_with_tags(store):
    pod_store_filter = EpisodeFilter(store=store, foo=True)
    assert _get_episode_ids(pod_store_filter.items) == ["222", "zzz"]


def test_episode_filter_without_tags(store):
    pod_store_filter = EpisodeFilter(store=store, foo=False)
    assert _get_episode_ids(pod_store_filter.items) == ["111", "aaa"]


def test_episode_filter_for_individual_episode(store):
    pod_store_filter = EpisodeFilter(
        store=store, podcast_title="greetings", episode_number=23
    )
    assert _get_episode_ids(pod_store_filter.items) == ["aaa"]


def test_episode_filter_for_range_of_podcast_episodes(store):
    pod_store_filter = EpisodeFilter(
        store=store,
        podcast_title="greetings",
        episode_range_start=11,
        episode_range_end=22,
    )
    assert _get_episode_ids(pod_store_filter.items) == ["zzz"]


def test_episode_filter_for_range_of_podcast_episodes_without_end(store):
    pod_store_filter = EpisodeFilter(
        store=store, podcast_title="greetings", episode_range_start=20
    )
    assert _get_episode_ids(pod_store_filter.items) == ["aaa"]


def test_episode_filter_for_range_of_podcast_episodes_without_start(store):
    pod_store_filter = EpisodeFilter(
        store=store, podcast_title="greetings", episode_range_end=11
    )
    assert _get_episode_ids(pod_store_filter.items) == ["zzz"]


def test_episode_filter_for_podcast(store):
    pod_store_filter = EpisodeFilter(store=store, podcast_title="greetings")
    assert _get_episode_ids(pod_store_filter.items) == ["aaa", "zzz"]


def test_episode_filter_for_podcasts_with_extra_podcast_filters(store):
    pod_store_filter = EpisodeFilter(store=store, podcast_filters={"hello": True})
    assert _get_episode_ids(pod_store_filter.items) == ["aaa", "zzz"]


def test_episode_filter_raises_exception_if_no_episodes_found(store):
    pod_store_filter = EpisodeFilter(store=store, tags=["whoooo"])
    with pytest.raises(NoEpisodesFoundError):
        pod_store_filter.items


def test_podcast_filter_all_podcasts(store):
    pod_store_filter = PodcastFilter(store=store)
    assert _get_podcast_titles(pod_store_filter.items) == [
        "farewell",
        "other",
        "greetings",
    ]


def test_podcast_filter_with_new_episodes(store):
    pod_store_filter = PodcastFilter(store=store, new_episodes=True)
    assert _get_podcast_titles(pod_store_filter.items) == ["farewell", "greetings"]


def test_podcast_filter_podcasts_with_tags(store):
    pod_store_filter = PodcastFilter(store=store, hello=True)
    assert _get_podcast_titles(pod_store_filter.items) == ["greetings"]


def test_podcast_filter_podcasts_without_tags(store):
    pod_store_filter = PodcastFilter(store=store, hello=False)
    assert _get_podcast_titles(pod_store_filter.items) == ["farewell", "other"]


def test_podcast_filter_single_podcast(store):
    pod_store_filter = PodcastFilter(
        store=store, new_episodes=True, podcast_title="farewell"
    )
    assert _get_podcast_titles(pod_store_filter.items) == ["farewell"]


def test_podcast_filter_raises_exception_if_no_podcasts_found(store):
    pod_store_filter = PodcastFilter(store=store, tags=["whoooo"])
    with pytest.raises(NoPodcastsFoundError):
        pod_store_filter.items
