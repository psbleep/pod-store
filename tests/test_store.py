import json
import os

import pytest

from pod_store import (
    DEFAULT_ENCRYPTED_STORE_FILE_NAME,
    DEFAULT_UNENCRYPTED_STORE_FILE_NAME,
    get_store_file_path,
)
from pod_store.exc import StoreExistsError, StoreIsNotEncrypted
from pod_store.store import Store
from pod_store.store_file_handlers import EncryptedStoreFileHandler

from . import TEST_GPG_ID_FILE_PATH, TEST_STORE_FILE_PATH, TEST_STORE_PATH

TEST_CUSTOM_STORE_FILE_PATH = os.path.join(TEST_STORE_PATH, "custom.file")


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.store.run_git_command")


@pytest.fixture
def custom_store_file_path(mocker):
    mocker.patch(
        "pod_store.get_store_file_path", return_value=TEST_CUSTOM_STORE_FILE_PATH
    )
    mocker.patch(
        "pod_store.store.get_store_file_path", return_value=TEST_CUSTOM_STORE_FILE_PATH
    )


def test_init_store_creates_store_directory_and_store_file_and_downloads_path(
    start_with_no_store,
):
    Store.init(
        setup_git=False,
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_UNENCRYPTED_STORE_FILE_NAME,
    )
    assert os.path.exists(TEST_STORE_FILE_PATH)


def test_init_store_setup_git_initializes_git_repo_and_sets_gitignore(
    start_with_no_store, mocked_run_git_command
):
    Store.init(
        setup_git=True,
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_UNENCRYPTED_STORE_FILE_NAME,
    )
    with open(os.path.join(TEST_STORE_PATH, ".gitignore")) as f:
        assert f.read() == ".gpg-id"
    mocked_run_git_command.assert_called_with("init")


def test_init_store_setup_git_with_git_url_clones_remote_repo(
    mocked_git_clone_with_store_file, start_with_no_store
):
    Store.init(
        setup_git=True,
        git_url="https://git.foo.bar/pod-store.git",
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_UNENCRYPTED_STORE_FILE_NAME,
    )
    mocked_git_clone_with_store_file.assert_called_with(
        f"git clone https://git.foo.bar/pod-store.git {TEST_STORE_PATH}"
    )
    assert os.path.exists(TEST_STORE_FILE_PATH)


def test_init_store_setup_git_with_git_url_will_create_store_file_if_repo_is_empty(
    mocked_git_clone_with_empty_repo, start_with_no_store
):
    Store.init(
        setup_git=True,
        git_url="https://git.foo.bar/pod-store.git",
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_UNENCRYPTED_STORE_FILE_NAME,
    )
    mocked_git_clone_with_empty_repo.assert_called_with(
        f"git clone https://git.foo.bar/pod-store.git {TEST_STORE_PATH}"
    )
    assert os.path.exists(TEST_STORE_FILE_PATH)


def test_init_store_setup_git_with_git_url_and_gpg_id_creates_gpg_id_file(
    mocked_git_clone_with_empty_repo, start_with_no_store
):
    Store.init(
        setup_git=True,
        git_url="https://git.foo.bar/pod-store.git",
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_ENCRYPTED_STORE_FILE_NAME,
        gpg_id="foo@bar.com",
    )
    mocked_git_clone_with_empty_repo.assert_called_with(
        f"git clone https://git.foo.bar/pod-store.git {TEST_STORE_PATH}",
    )
    with open(TEST_GPG_ID_FILE_PATH) as f:
        assert f.read() == "foo@bar.com"


def test_init_store_with_gpg_id_sets_gpg_id_file_and_creates_encrypted_store_file(
    start_with_no_store,
):
    Store.init(
        gpg_id="hello@world.com",
        setup_git=False,
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_ENCRYPTED_STORE_FILE_NAME,
    )

    with open(os.path.join(TEST_STORE_PATH, ".gpg-id")) as f:
        assert f.read() == "hello@world.com"


def test_init_store_already_exists():
    with pytest.raises(StoreExistsError):
        Store.init(
            setup_git=False,
            store_path=TEST_STORE_PATH,
            store_file_name=DEFAULT_UNENCRYPTED_STORE_FILE_NAME,
        )


def test_store_encrypt_sets_up_encrypted_store_file_and_cleans_up_old_store_data(
    mocker,
    store_data,
    store,
):
    encrypted_store_file_path = get_store_file_path(gpg_id=True)
    mocked_create_encrypted_store_file = mocker.patch(
        "pod_store.store.EncryptedStoreFileHandler.create_store_file"
    )

    store.encrypt("zoo@baz.com")

    with open(TEST_GPG_ID_FILE_PATH) as f:
        assert f.read() == "zoo@baz.com"

    mocked_create_encrypted_store_file.assert_called_with(
        gpg_id="zoo@baz.com",
        store_file_path=encrypted_store_file_path,
        store_data=store_data,
    )
    assert not os.path.exists(TEST_STORE_FILE_PATH)


def test_store_encrypt_does_not_delete_new_store_file_if_name_is_same_as_old(
    mocker,
    custom_store_file_path,
    store_data,
    store,
):
    def _create_store_file(*args, **kwargs):
        with open(TEST_CUSTOM_STORE_FILE_PATH, "w") as f:
            f.write("")

    mocker.patch(
        "pod_store.store.EncryptedStoreFileHandler.create_store_file",
        side_effect=_create_store_file,
    )

    file_handler = EncryptedStoreFileHandler(
        store_file_path=TEST_CUSTOM_STORE_FILE_PATH, gpg_id="oof@rab.com"
    )
    file_handler.read_data = mocker.Mock(return_value=store_data)

    store = Store(
        store_path=TEST_STORE_PATH,
        file_handler=file_handler,
    )

    store.encrypt("zoo@baz.com")
    assert os.path.exists(TEST_CUSTOM_STORE_FILE_PATH)


def test_unencrypt_writes_unencrypted_store_file_cleans_up_old_store_data(
    mocker, start_with_no_store, store_data
):
    encrypted_store_file_path = get_store_file_path(gpg_id=True)

    Store.init(
        store_path=TEST_STORE_PATH,
        store_file_name=DEFAULT_ENCRYPTED_STORE_FILE_NAME,
        setup_git=False,
        gpg_id="oof@rab.com",
    )

    file_handler = EncryptedStoreFileHandler(
        store_file_path=encrypted_store_file_path, gpg_id="oof@rab.com"
    )
    file_handler.read_data = mocker.Mock(return_value=store_data)

    store = Store(
        store_path=TEST_STORE_PATH,
        file_handler=file_handler,
    )
    with open(encrypted_store_file_path, "w") as f:
        f.write("")

    store.unencrypt()

    assert not os.path.exists(TEST_GPG_ID_FILE_PATH)
    assert not os.path.exists(encrypted_store_file_path)

    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f) == store_data


def test_unencrypt_does_not_delete_new_store_file_if_has_same_name_as_old(
    mocker, custom_store_file_path, start_with_no_store, store_data
):
    Store.init(
        store_path=TEST_STORE_PATH,
        store_file_name="custom.file",
        setup_git=False,
        gpg_id="oof@rab.com",
    )

    file_handler = EncryptedStoreFileHandler(
        store_file_path=TEST_CUSTOM_STORE_FILE_PATH, gpg_id="oof@rab.com"
    )
    file_handler.read_data = mocker.Mock(return_value=store_data)

    store = Store(
        store_path=TEST_STORE_PATH,
        file_handler=file_handler,
    )

    store.unencrypt()

    with open(TEST_CUSTOM_STORE_FILE_PATH) as f:
        assert json.load(f) == store_data


def test_unencrypt_store_raises_error_if_store_is_not_encrypted(store):
    with pytest.raises(StoreIsNotEncrypted):
        store.unencrypt()


def test_save_writes_data_to_file(store_data, store):
    store.podcasts.get("greetings").title = "updated"
    store.save()
    with open(TEST_STORE_FILE_PATH) as f:
        assert json.load(f)["greetings"]["title"] == "updated"
