import os

import pytest

from pod_store.exc import PodcastDoesNotExistError, PodcastExistsError
from pod_store.store import StorePodcasts

from . import TEST_PODCAST_DOWNLOADS_PATH


@pytest.fixture
def store_podcasts(store_podcasts_data):
    return StorePodcasts(
        podcast_data=store_podcasts_data,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
    )


def test_store_podcasts_add_podcast(store_podcasts):
    podcast = store_podcasts.add(title="zoobar", feed="http://zoo.bar/rss")
    assert podcast.title == "zoobar"
    assert podcast.episode_downloads_path == os.path.join(
        TEST_PODCAST_DOWNLOADS_PATH, "zoobar"
    )


def test_store_podcasts_add_podcast_with_title_already_exists(store_podcasts):
    with pytest.raises(PodcastExistsError):
        store_podcasts.add(title="greetings", feed="http://new.bar/rss")


def test_store_podcasts_delete_podcast(store_podcasts):
    store_podcasts.delete("greetings")
    assert "greetings" not in store_podcasts._podcasts


def test_store_podcasts_delete_podcast_does_not_exist(store_podcasts):
    with pytest.raises(PodcastDoesNotExistError):
        store_podcasts.delete("zabababa")


def test_store_podcasts_get_podcast(store_podcasts):
    assert store_podcasts.get("farewell").title == "farewell"


def test_store_podcasts_get_podcast_raises_error_if_not_found(store_podcasts):
    with pytest.raises(PodcastDoesNotExistError):
        store_podcasts.get("ababababa")


def test_store_podcasts_list_podcasts_sorts_by_order_created(store_podcasts):
    pod1, pod2 = store_podcasts.list()
    assert pod1.title == "farewell"
    assert pod2.title == "greetings"


def test_store_podcasts_list_with_filters(store_podcasts):
    pods = store_podcasts.list(has_new_episodes=True)
    assert len(pods) == 1
    assert pods[0].title == "greetings"


def test_store_podcasts_rename(store_podcasts):
    store_podcasts.rename("greetings", "hellos")
    assert "greetings" not in store_podcasts._podcasts
    assert store_podcasts._podcasts["hellos"].episode_downloads_path == os.path.join(
        TEST_PODCAST_DOWNLOADS_PATH, "hellos"
    )


def test_store_podcasts_rename_old_title_does_not_exist(store_podcasts):
    with pytest.raises(PodcastDoesNotExistError):
        store_podcasts.rename("zazaza", "abababaaa")


def test_store_podcasts_rename_new_title_already_exists(store_podcasts):
    with pytest.raises(PodcastExistsError):
        store_podcasts.rename("greetings", "farewell")


def test_store_podcasts_to_json(store_podcasts, store_podcasts_data):
    assert store_podcasts.to_json() == store_podcasts_data
