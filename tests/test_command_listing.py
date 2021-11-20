from collections import namedtuple

import pytest

from pod_store.commands.filtering import EpisodeFilter, PodcastFilter
from pod_store.commands.listing import Lister, episodes_presenter, podcasts_presenter
from pod_store.exc import NoEpisodesFoundError

fake_terminal_size = namedtuple("fake_terminal_size", ["columns"])


@pytest.fixture(autouse=True)
def fake_terminal_width(mocker):
    mocker.patch(
        "pod_store.commands.listing.get_terminal_size",
        return_value=fake_terminal_size(columns=5),
    )


@pytest.fixture
def episode_lister(store):
    pod_store_filter = EpisodeFilter(store=store)
    return Lister(pod_store_filter=pod_store_filter, presenter=episodes_presenter)


@pytest.fixture
def podcast_lister(store):
    pod_store_filter = PodcastFilter(store=store)
    return Lister(pod_store_filter=pod_store_filter, presenter=podcasts_presenter)


def test_lister_from_command_arguments_provides_an_episode_lister_when_indicated(store):
    lister = Lister.from_command_arguments(store=store, list_episodes=True)
    assert lister.presenter == episodes_presenter


def test_lister_from_command_arguments_provides_a_podcast_lister_when_indiciated(store):
    lister = Lister.from_command_arguments(store=store, list_episodes=False)
    assert lister.presenter == podcasts_presenter


def test_episode_lister_list(episode_lister):
    assert list(episode_lister.list_items()) == [
        "farewell",
        "[0001] gone: 'all' -> new, bar",
        "[0002] not forgotten: 'never' -> foo, bar",
        "",
        "greetings",
        "[0023] hello: 'hello' -> new",
        "[0011] goodbye: 'goodbye' [X] -> foo",
    ]


def test_episode_lister_list_verbose_mode(
    yesterday_formatted, now_formatted, episode_lister
):
    assert list(episode_lister.list_items(verbose=True)) == [
        "farewell",
        f"""[0001] gone
id: 111
tags: new, bar
created at: {now_formatted}
updated at: {now_formatted}
all gone (longer description)""",
        "",
        f"""[0002] not forgotten
id: 222
tags: foo, bar
created at: {now_formatted}
updated at: {now_formatted}
never forgotten (longer description)""",
        "",
        "greetings",
        f"""[0023] hello
id: aaa
tags: new
created at: {now_formatted}
updated at: {now_formatted}
hello world (longer description)""",
        "",
        f"""[0011] goodbye
id: zzz
tags: foo
created at: {yesterday_formatted}
updated at: {yesterday_formatted}
downloaded at: {now_formatted}
goodbye world (longer description)""",
    ]


def test_episode_lister_allows_empty_short_description(store, episode_lister):
    podcast = store.podcasts.get("greetings")
    episode = podcast.episodes.get("aaa")
    episode.short_description = ""

    assert "[0023] hello: (no description) -> new" in list(episode_lister.list_items())


def test_episode_lister_allows_empty_long_description_in_verbose_mode(
    store, episode_lister
):
    podcast = store.podcasts.get("farewell")
    episode = podcast.episodes.get("111")
    episode.long_description = ""

    verbose_episode_listing = list(episode_lister.list_items(verbose=True))[1]
    assert "(no description)" in verbose_episode_listing


def test_episode_lister_list_raises_exception_when_no_episodes_found(store):
    pod_store_filter = EpisodeFilter(store=store, tags=["whoooooo"])
    episode_lister = Lister(
        pod_store_filter=pod_store_filter, presenter=episodes_presenter
    )
    with pytest.raises(NoEpisodesFoundError):
        list(episode_lister.list_items())


def test_podcast_lister_list(podcast_lister):
    assert list(podcast_lister.list_items()) == [
        "farewell [1]",
        "other -> inactive",
        "greetings [1] -> hello",
    ]


def test_podcast_lister_list_verbose_mode(
    yesterday_formatted, now_formatted, podcast_lister
):
    assert list(podcast_lister.list_items(verbose=True)) == [
        f"""farewell
1 new episodes
feed: http://goodbye.world/rss
created at: {yesterday_formatted}
updated at: {now_formatted}""",
        "",
        f"""other
0 new episodes
tags: inactive
feed: http://other.thing/rss
created at: {yesterday_formatted}
updated at: {now_formatted}""",
        "",
        f"""greetings
1 new episodes
tags: hello
feed: http://hello.world/rss
created at: {now_formatted}
updated at: {now_formatted}""",
    ]
