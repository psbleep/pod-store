from datetime import datetime
from subprocess import CalledProcessError

import pytest

from pod_store import util
from pod_store.exc import ShellCommandError

from . import TEST_STORE_PATH, fake_process


def test_util_parse_datetime_from_json():
    assert util.parse_datetime_from_json("2021-01-01T01:01:01") == datetime(
        2021, 1, 1, 1, 1, 1
    )


def test_util_parse_datetime_from_json_tolerates_null():
    assert util.parse_datetime_from_json(None) is None


def test_util_parse_datetime_to_json():
    assert (
        util.parse_datetime_to_json(datetime(2021, 1, 1, 1, 1, 1))
        == "2021-01-01T01:01:01"
    )


def test_util_parse_datetime_to_json_tolerates_null():
    assert util.parse_datetime_to_json(None) is None


def test_util_run_git_command(mocked_subprocess_run):
    mocked_subprocess_run.configure_mock(
        **{"return_value": fake_process(stdout=b"added the things", stderr=b"")}
    )
    assert util.run_git_command("add .") == "added the things"
    mocked_subprocess_run.assert_called_with(
        "git add .",
        cwd=TEST_STORE_PATH,
        capture_output=True,
        check=True,
        shell=True,
    )


def test_util_run_shell_command(mocked_subprocess_run):
    mocked_subprocess_run.configure_mock(
        **{"return_value": fake_process(stdout=b"command was good", stderr=b"")}
    )
    assert util.run_shell_command("hello world") == "command was good"
    mocked_subprocess_run.assert_called_with(
        "hello world",
        cwd=None,
        capture_output=True,
        check=True,
        shell=True,
    )


def test_util_run_shell_command_returns_stderr_if_no_stdout(mocked_subprocess_run):
    mocked_subprocess_run.configure_mock(
        **{"return_value": fake_process(stdout=b"", stderr=b"output hidden")}
    )
    assert util.run_shell_command("hello world") == "output hidden"


def test_util_run_shell_command_encounters_error(mocked_subprocess_run):
    mocked_subprocess_run.configure_mock(
        **{
            "side_effect": CalledProcessError(
                returncode=1, cmd="zzzz", stderr=b"not a thing"
            )
        }
    )
    with pytest.raises(ShellCommandError):
        util.run_shell_command("zzzzz")
