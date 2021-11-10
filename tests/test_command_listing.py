from collections import namedtuple

import pytest

from pod_store.commands.filtering import EpisodeFilter, PodcastFilter
from pod_store.commands.listing import EpisodeLister, PodcastLister
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
    filter = EpisodeFilter(store=store)
    return EpisodeLister(filter=filter)


@pytest.fixture
def podcast_lister(store):
    filter = PodcastFilter(store=store)
    return PodcastLister(filter=filter)


def test_episode_lister_list(episode_lister):
    assert list(episode_lister.list()) == [
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
    assert list(episode_lister.list(verbose=True)) == [
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

    assert "[0023] hello: (no description) -> new" in list(episode_lister.list())


def test_episode_lister_allows_empty_long_description_in_verbose_mode(
    store, episode_lister
):
    podcast = store.podcasts.get("farewell")
    episode = podcast.episodes.get("111")
    episode.long_description = ""

    verbose_episode_listing = list(episode_lister.list(verbose=True))[1]
    assert "(no description)" in verbose_episode_listing


def test_episode_lister_list_raises_exception_when_no_episodes_found(store):
    filter = EpisodeFilter(store=store, tags=["whoooooo"])
    episode_lister = EpisodeLister(filter=filter)
    with pytest.raises(NoEpisodesFoundError):
        list(episode_lister.list())


def test_podcast_lister_list(podcast_lister):
    assert list(podcast_lister.list()) == [
        "farewell [1]",
        "other",
        "greetings [1] -> hello",
    ]


def test_podcast_lister_list_verbose_mode(
    yesterday_formatted, now_formatted, podcast_lister
):
    assert list(podcast_lister.list(verbose=True)) == [
        f"""farewell
1 new episodes
feed: http://goodbye.world/rss
created at: {yesterday_formatted}
updated at: {now_formatted}""",
        "",
        f"""other
0 new episodes
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
