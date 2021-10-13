import json
import os
from subprocess import CalledProcessError
from unittest.mock import ANY

import pytest

from pod_store.exc import GPGCommandError
from pod_store.store_file_handlers import (
    EncryptedStoreFileHandler,
    UnencryptedStoreFileHandler,
)

from . import TEST_STORE_FILE_PATH, TEST_STORE_PATH, fake_process

ENCRYPTED_FILE_HANDLER_TMP_STORE_FILE_PATH = os.path.join(TEST_STORE_PATH, ".tmp")


@pytest.fixture
def encrypted_store_file_handler():
    return EncryptedStoreFileHandler(
        store_file_path=TEST_STORE_FILE_PATH, gpg_id="foo@bar.com"
    )


def test_encrypted_store_file_handler_read_data(
    mocked_subprocess_run, encrypted_store_file_handler
):
    mocked_subprocess_run.configure_mock(
        **{
            "return_value": fake_process(
                stdout=b'{"hello": "world"}', stderr=b"gpg: encrypted with stuff"
            )
        }
    )

    # write fake encrypted data to store file
    with open(TEST_STORE_FILE_PATH, "w") as f:
        f.write("27837ss282938918479107138901893018903189038908390189031")

    assert encrypted_store_file_handler.read_data() == {"hello": "world"}
    mocked_subprocess_run.assert_called_with(
        f"gpg -d {TEST_STORE_FILE_PATH}", capture_output=True, check=True, shell=True
    )


def test_encrypted_store_file_handler_write_data(
    mocker, mocked_subprocess_run, encrypted_store_file_handler
):
    mocked_json_dump = mocker.patch("pod_store.store_file_handlers.json.dump")
    mocked_subprocess_run.configure_mock(
        **{"return_value": fake_process(stdout=b"", stderr=b"")}
    )

    gpg_cmd = (
        f"gpg --output {TEST_STORE_FILE_PATH} "
        "--encrypt "
        "--recipient foo@bar.com "
        f"{ENCRYPTED_FILE_HANDLER_TMP_STORE_FILE_PATH}"
    )

    encrypted_store_file_handler.write_data({"foo": "bar"})

    mocked_json_dump.assert_called_with({"foo": "bar"}, ANY)

    mocked_subprocess_run.assert_called_with(
        gpg_cmd,
        capture_output=True,
        check=True,
        shell=True,
    )

    assert not os.path.exists(ENCRYPTED_FILE_HANDLER_TMP_STORE_FILE_PATH)


def test_encrypted_store_file_handler_cleans_up_during_write_error(
    mocked_subprocess_run,
    encrypted_store_file_handler,
):
    mocked_subprocess_run.configure_mock(
        **{
            "return_value": CalledProcessError(
                returncode=1, cmd="gpg stuff", stderr=b"too good"
            )
        }
    )

    encrypted_data = b"3892890328902389028902"
    with open(TEST_STORE_FILE_PATH, "wb") as f:
        f.write(encrypted_data)

    with pytest.raises(GPGCommandError):
        encrypted_store_file_handler.write_data({"foo": "bar"})

    assert not os.path.exists(ENCRYPTED_FILE_HANDLER_TMP_STORE_FILE_PATH)
    with open(TEST_STORE_FILE_PATH, "rb") as f:
        assert f.read() == encrypted_data


def test_unencrypted_store_file_handler_create_store_file():
    UnencryptedStoreFileHandler.create_store_file(TEST_STORE_FILE_PATH)
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
