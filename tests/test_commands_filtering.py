from pod_store.commands.filtering import EpisodeFilter, PodcastFilter


def _get_episode_ids(episodes):
    return [e.id for e in episodes]


def _get_podcast_titles(podcasts):
    return [p.title for p in podcasts]


def test_episode_filter_all_episodes(store):
    filter = EpisodeFilter(
        store=store,
    )
    assert _get_episode_ids(filter.episodes) == ["111", "222", "aaa", "zzz"]


def test_episode_filter_new_episodes(store):
    filter = EpisodeFilter(store=store, new_episodes=True)
    assert _get_episode_ids(filter.episodes) == ["111", "aaa"]


def test_episode_filter_with_tags(store):
    filter = EpisodeFilter(store=store, tags=["foo"])
    assert _get_episode_ids(filter.episodes) == ["222", "zzz"]


def test_episode_filter_without_tags(store):
    filter = EpisodeFilter(store=store, tags=["foo"], list_untagged_items=True)
    assert _get_episode_ids(filter.episodes) == ["111", "aaa"]


def test_episode_filter_for_podcast(store):
    filter = EpisodeFilter(store=store, podcast_title="greetings")
    assert _get_episode_ids(filter.episodes) == ["aaa", "zzz"]


def test_podcast_filter_all_podcasts(store):
    filter = PodcastFilter(store=store)
    assert _get_podcast_titles(filter.podcasts) == ["farewell", "other", "greetings"]


def test_podcast_filter_with_new_episodes(store):
    filter = PodcastFilter(store=store, new_episodes=True)
    assert _get_podcast_titles(filter.podcasts) == ["farewell", "greetings"]


def test_podcast_filter_list_podcasts_with_tags(store):
    filter = PodcastFilter(store=store, tags=["hello"])
    assert _get_podcast_titles(filter.podcasts) == ["greetings"]


def test_podcast_filter_list_podcasts_without_tags(store):
    filter = PodcastFilter(store=store, tags=["hello"], list_untagged_items=True)
    assert _get_podcast_titles(filter.podcasts) == ["farewell", "other"]


def test_podcast_filter_single_podcast(store):
    filter = PodcastFilter(store=store, new_episodes=True, podcast_title="farewell")
    assert _get_podcast_titles(filter.podcasts) == ["farewell"]
