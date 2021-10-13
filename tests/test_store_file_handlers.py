import json

from pod_store.store_file_handlers import UnencryptedStoreFileHandler

from . import TEST_STORE_FILE_PATH


def test_unencrypted_store_file_handler_create_store_file():
    UnencryptedStoreFileHandler.create_with_file(TEST_STORE_FILE_PATH)
    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f) == {}


def test_unencrypted_store_file_handler_read_data_loads_json_from_file(
    store_podcasts_data, unencrypted_store_file_handler
):
    assert unencrypted_store_file_handler.read_data() == store_podcasts_data


def test_unencrypted_store_file_handler_write_data_writes_json_to_file(
    store_podcasts_data, unencrypted_store_file_handler
):
    store_podcasts_data["greetings"]["title"] == "greetings-updated"
    unencrypted_store_file_handler.write_data(store_podcasts_data)
    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f) == store_podcasts_data
