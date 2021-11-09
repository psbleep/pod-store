import pytest

from pod_store.exc import (
    PodcastDoesNotExistError,
    PodcastExistsError,
)
from pod_store.store import StorePodcasts


@pytest.fixture
def store_podcasts(store_data):
    return StorePodcasts(podcast_data=store_data)


def test_store_podcasts_add_podcast(store_podcasts):
    podcast = store_podcasts.add(title="zoobar", feed="http://zoo.bar/rss")
    assert podcast.title == "zoobar"


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


def test_store_podcasts_lists_podcasts_sorted_by_created_at(store_podcasts):
    pod1, pod2, pod3 = store_podcasts.list()
    assert pod1.title == "farewell"
    assert pod2.title == "other"
    assert pod3.title == "greetings"


def test_store_podcasts_rename(store_podcasts):
    store_podcasts.rename("greetings", "hellos")
    assert "greetings" not in store_podcasts._podcasts
    assert store_podcasts._podcasts["hellos"].title == "hellos"


def test_store_podcasts_rename_old_title_does_not_exist(store_podcasts):
    with pytest.raises(PodcastDoesNotExistError):
        store_podcasts.rename("zazaza", "abababaaa")


def test_store_podcasts_rename_new_title_already_exists(store_podcasts):
    with pytest.raises(PodcastExistsError):
        store_podcasts.rename("greetings", "farewell")


def test_store_podcasts_to_json(store_podcasts, store_data):
    assert store_podcasts.to_json() == store_data
