from collections import namedtuple

import pytest

from pod_store.exc import NoEpisodesFoundError, NoPodcastsFoundError

from pod_store.commands.listing import EpisodeLister, PodcastLister


fake_terminal_size = namedtuple("fake_terminal_size", ["columns"])


@pytest.fixture(autouse=True)
def fake_terminal_width(mocker):
    mocker.patch(
        "pod_store.commands.listing.get_terminal_size",
        return_value=fake_terminal_size(columns=5),
    )


def test_episode_lister_list_new_episodes(store):
    lister = EpisodeLister(store=store, new_episodes=True)
    assert list(lister.list()) == [
        "farewell",
        "[0001] gone: 'all' -> new, bar",
        "",
        "greetings",
        "[0023] hello: 'hello' -> new",
    ]


def test_episode_lister_list_all_episodes(store):
    lister = EpisodeLister(store=store, new_episodes=False)
    assert list(lister.list()) == [
        "farewell",
        "[0001] gone: 'all' -> new, bar",
        "[0002] not forgotten: 'never' -> foo, bar",
        "",
        "greetings",
        "[0023] hello: 'hello' -> new",
        "[0011] goodbye: 'goodbye' [X] -> foo",
    ]


def test_episode_lister_episodes_with_tags(store):
    lister = EpisodeLister(store=store, new_episodes=False, tags=["foo"])
    assert list(lister.list()) == [
        "farewell",
        "[0002] not forgotten: 'never' -> foo, bar",
        "",
        "greetings",
        "[0011] goodbye: 'goodbye' [X] -> foo",
    ]


def test_episode_lister_episodes_without_tags(store):
    lister = EpisodeLister(
        store=store, new_episodes=False, tags=["foo"], list_untagged_items=True
    )
    assert list(lister.list()) == [
        "farewell",
        "[0001] gone: 'all' -> new, bar",
        "",
        "greetings",
        "[0023] hello: 'hello' -> new",
    ]


def test_episode_lister_list_episodes_for_podcast(store):
    lister = EpisodeLister(store=store, new_episodes=False, podcast_title="greetings")
    assert list(lister.list()) == [
        "greetings",
        "[0023] hello: 'hello' -> new",
        "[0011] goodbye: 'goodbye' [X] -> foo",
    ]


def test_episode_lister_get_episodes(store):
    lister = EpisodeLister(store=store)
    assert list(map(lambda e: e.id, lister.get_episodes())) == ["111", "aaa"]


def test_episode_lister_verbose_mode(yesterday_formatted, now_formatted, store):
    lister = EpisodeLister(store=store, new_episodes=False, verbose=True)
    assert list(lister.list()) == [
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


def test_episode_lister_no_episodes_matching_criteria(store):
    lister = EpisodeLister(store=store, tags=["whooo"])
    with pytest.raises(NoEpisodesFoundError):
        list(lister.list())


def test_podcast_lister_list_podcasts_with_new_episodes(store):
    lister = PodcastLister(store=store, new_episodes=True)
    assert list(lister.list()) == ["farewell [1]", "greetings [1] -> hello"]


def test_podcast_lister_list_all_podcasts(store):
    lister = PodcastLister(store=store, new_episodes=False)
    assert list(lister.list()) == ["farewell [1]", "other", "greetings [1] -> hello"]


def test_podcast_lister_list_podcasts_with_tags(store):
    lister = PodcastLister(store=store, tags=["hello"])
    assert list(lister.list()) == ["greetings [1] -> hello"]


def test_podcast_lister_list_podcasts_without_tags(store):
    lister = PodcastLister(store=store, tags=["hello"], list_untagged_items=True)
    assert list(lister.list()) == ["farewell [1]"]


def test_podcast_lister_verbose_mode(yesterday_formatted, now_formatted, store):
    lister = PodcastLister(store=store, verbose=True)
    assert list(lister.list()) == [
        f"""farewell
1 new episodes
feed: http://goodbye.world/rss
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


def test_podcast_lister_single_podcast(store):
    lister = PodcastLister(store=store, new_episodes=True, podcast_title="farewell")
    assert list(lister.list()) == ["farewell [1]"]


def test_podcast_lister_list_single_podcast_will_list_podcast_without_new_episodes(
    store,
):
    lister = PodcastLister(store=store, new_episodes=True, podcast_title="other")
    assert list(lister.list()) == ["other"]


def test_podcast_lister_without_podcasts_matching_criteria(store):
    lister = PodcastLister(store=store, tags=["super"])
    with pytest.raises(NoPodcastsFoundError):
        list(lister.list())
