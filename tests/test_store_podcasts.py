import pytest

from pod_store.exc import (
    NoPodcastsFoundError,
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


def test_store_podcasts_lists_podcasts_filtered_by_attribute(store_podcasts):
    pod1, pod2 = store_podcasts.list(has_new_episodes=True)
    assert pod1.title == "farewell"
    assert pod2.title == "greetings"


def test_store_podcasts_lists_podcasts_filtered_by_presence_of_tag(store_podcasts):
    pod = store_podcasts.get("greetings")
    pod.tags = ["zoobar"]

    pods = store_podcasts.list(zoobar=True)
    assert len(pods) == 1
    assert pods[0].title == "greetings"


def test_store_podcasts_lists_podcasts_filtered_by_absence_of_tag(store_podcasts):
    pod = store_podcasts.get("greetings")
    pod.tags = ["zoobar"]

    pods = store_podcasts.list(zoobar=False)
    assert len(pods) == 2


def test_store_podcasts_list_raises_attribute_error_if_filter_is_not_attribute_or_tag(
    store_podcasts,
):
    with pytest.raises(AttributeError):
        store_podcasts.list(zozo="hello")


def test_store_podcasts_list_no_podcasts_found_raises_error_when_empty_not_allowed(
    store_podcasts,
):
    with pytest.raises(NoPodcastsFoundError):
        store_podcasts.list(allow_empty=False, title="zzzzzzz")


def test_store_podcasts_list_no_podcasts_found_returns_empty_list_when_empty_is_allowed(
    store_podcasts,
):
    assert store_podcasts.list(allow_empty=True, title="zzzzzzzzz") == []


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
