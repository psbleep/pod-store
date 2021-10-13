import json

from pod_store.store import StoreFileHandler

from . import TEST_STORE_FILE_PATH


def test_store_file_handler_create_store_file():
    StoreFileHandler.create_with_file(TEST_STORE_FILE_PATH)
    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f) == {}


def test_store_file_handler_read_data_loads_json_from_file(
    store_podcasts_data, store_file_handler
):
    assert store_file_handler.read_data() == store_podcasts_data


def test_store_file_handler_write_data_writes_json_to_file(
    store_podcasts_data, store_file_handler
):
    store_podcasts_data["greetings"]["title"] == "greetings-updated"
    store_file_handler.write_data(store_podcasts_data)
    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f) == store_podcasts_data
