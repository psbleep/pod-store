import json
import os
from unittest.mock import call

import pytest

from pod_store.exc import StoreExistsError
from pod_store.store import Store
from pod_store.store_file_handlers import EncryptedStoreFileHandler

from . import (
    TEST_GPG_ID_FILE_PATH,
    TEST_PODCAST_DOWNLOADS_PATH,
    TEST_STORE_FILE_PATH,
    TEST_STORE_PATH,
)


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.store.run_git_command")


def test_init_store_creates_store_directory_and_store_file_and_downloads_path(
    start_with_no_store,
):
    Store.init(
        setup_git=False,
        store_path=TEST_STORE_PATH,
        store_file_path=TEST_STORE_FILE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
    )
    assert os.path.exists(TEST_STORE_FILE_PATH)


def test_init_store_already_exists():
    with pytest.raises(StoreExistsError):
        Store.init(
            setup_git=False,
            store_path=TEST_STORE_PATH,
            store_file_path=TEST_STORE_FILE_PATH,
            podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
        )


def test_init_store_setup_git_initializes_git_repo_and_sets_gitignore(
    start_with_no_store, mocked_run_git_command
):
    Store.init(
        setup_git=True,
        store_path=TEST_STORE_PATH,
        store_file_path=TEST_STORE_FILE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
    )
    with open(os.path.join(TEST_STORE_PATH, ".gitignore")) as f:
        assert f.read() == ".gpg-id"
    mocked_run_git_command.assert_called_with("init")


def test_init_store_setup_git_with_git_url_establishes_repo_remote_origin(
    start_with_no_store, mocked_run_git_command
):
    Store.init(
        setup_git=True,
        git_url="https://git.foo.bar/pod-store.git",
        store_path=TEST_STORE_PATH,
        store_file_path=TEST_STORE_FILE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
    )
    mocked_run_git_command.assert_has_calls(
        [
            call("init"),
            call("remote add origin https://git.foo.bar/pod-store.git"),
        ]
    )


def test_init_store_with_gpg_id_sets_gpg_id_file_and_creates_encrypted_store_file(
    start_with_no_store,
):
    Store.init(
        gpg_id="hello@world.com",
        setup_git=False,
        store_path=TEST_STORE_PATH,
        store_file_path=TEST_STORE_FILE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
    )

    with open(os.path.join(TEST_STORE_PATH, ".gpg-id")) as f:
        assert f.read() == "hello@world.com"


def test_store_encrypt_reads_existing_store_data_and_sets_up_encrypted_store_and_file(
    mocker,
    store_data,
    store,
):
    mocked_create_encrypted_store_file = mocker.patch(
        "pod_store.store.EncryptedStoreFileHandler.create_store_file"
    )

    store.encrypt("zoo@baz.com")

    with open(TEST_GPG_ID_FILE_PATH) as f:
        assert f.read() == "zoo@baz.com"

    mocked_create_encrypted_store_file.assert_called_with(
        gpg_id="zoo@baz.com",
        store_file_path=TEST_STORE_FILE_PATH,
        store_data=store_data,
    )


def test_unencrypt_reads_existing_store_data_and_writes_unencrypted_store_file(
    mocker, start_with_no_store, store_data
):
    Store.init(
        store_path=TEST_STORE_PATH,
        store_file_path=TEST_STORE_FILE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
        setup_git=False,
        gpg_id="oof@rab.com",
    )

    file_handler = EncryptedStoreFileHandler(
        store_file_path=TEST_STORE_FILE_PATH, gpg_id="oof@rab.com"
    )
    file_handler.read_data = mocker.Mock(return_value=store_data)

    store = Store(
        store_path=TEST_STORE_PATH,
        podcast_downloads_path=TEST_PODCAST_DOWNLOADS_PATH,
        file_handler=file_handler,
    )

    store.unencrypt()

    assert not os.path.exists(TEST_GPG_ID_FILE_PATH)

    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f) == store_data


def test_save_writes_data_to_file(store_data, store):
    store.podcasts.get("greetings").title = "updated"
    store.save()
    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f)["greetings"]["title"] == "updated"
