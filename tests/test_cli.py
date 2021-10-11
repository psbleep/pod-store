from unittest.mock import Mock, call

import pytest
from click.testing import CliRunner

from pod_store.__main__ import cli
from pod_store.exc import GitCommandError

from . import TEST_DOWNLOAD_PATH, TEST_STORE_PATH


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.__main__.run_git_command")


def _assert_git_changes_commited(mocked: Mock, commit_msg: str):
    mocked.assert_has_calls([call("add ."), call(f"commit -m {commit_msg!r}")])


@pytest.fixture
def runner():
    return CliRunner()


def test_init(start_with_no_store, runner):
    result = runner.invoke(cli, ["init", "--no-git"])
    assert result.exit_code == 0
    assert result.output == (
        f"Store created: {TEST_STORE_PATH}\n"
        f"Podcast episodes will be downloaded to {TEST_DOWNLOAD_PATH}\n"
    )


def test_init_with_git(start_with_no_store, runner):
    result = runner.invoke(cli, ["init", "--git"])
    assert result.exit_code == 0
    assert result.output.endswith(
        "Git tracking enabled: no remote repo specified. "
        "You can manually add one later.\n"
    )


def test_init_with_git_url(start_with_no_store, runner):
    result = runner.invoke(cli, ["init", "-g", "https://git.foo.bar/pypod-store.git"])
    assert result.exit_code == 0
    assert result.output.endswith(
        "Git tracking enabled: https://git.foo.bar/pypod-store.git\n"
    )


def test_ls_all_podcasts(runner):
    result = runner.invoke(cli, ["ls", "--all"])
    assert result.exit_code == 0
    assert result.output == "a/1\nb\nc/2\nc/d/3\n"


def test_ls_podcasts_with_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--new"])
    assert result.exit_code == 0
    assert result.output == "b\n"


def test_ls_all_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "-p", "b", "--all"])
    assert result.exit_code == 0
    assert result.output == "[0092] hello\n[0082] goodbye\n"


def test_ls_new_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "-p", "b", "--new"])
    assert result.exit_code == 0
    assert result.output == "[0092] hello\n"


def test_ls_all_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all"])
    assert result.exit_code == 0
    assert (
        result.output
        == "b -> [0092] hello\nb -> [0082] goodbye\nc/2 -> [0011] old news\n"
    )


def test_ls_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--new"])
    assert result.exit_code == 0
    assert result.output == "b -> [0092] hello\n"


def test_add(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["add", "hello", "https://www.hello.world/rss"])
    assert result.exit_code == 0
    _assert_git_changes_commited(mocked_run_git_command, "Added podcast")


def test_rm(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["rm", "c/d/3"])
    assert result.exit_code == 0
    _assert_git_changes_commited(mocked_run_git_command, "Removed podcast")


def test_mark_interactive_marks_when_confirmed(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["mark", "--interactive"], input="y\n")
    assert result.exit_code == 0
    assert result.output.endswith("Marking b -> [0092] hello\n")
    _assert_git_changes_commited(mocked_run_git_command, "Marked podcast episodes")


def test_mark_interactive_does_not_mark_when_not_confirmed(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["mark", "--interactive"], input="n\n")
    assert result.exit_code == 0
    assert "Marking b -> hello\n" not in result.output
    _assert_git_changes_commited(mocked_run_git_command, "Marked podcast episodes")


def test_mark_bulk(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["mark", "--bulk"])
    assert result.exit_code == 0
    assert result.output == "Marking b -> [0092] hello\n"
    _assert_git_changes_commited(mocked_run_git_command, "Marked podcast episodes")


def test_mv(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["mv", "a/1", "a"])
    assert result.exit_code == 0
    _assert_git_changes_commited(mocked_run_git_command, "Renamed podcast")


def test_refresh_all_podcasts(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["refresh"])
    assert result.exit_code == 0
    assert (
        result.output
        == "Refreshing a/1\nRefreshing b\nRefreshing c/2\nRefreshing c/d/3\n"
    )
    _assert_git_changes_commited(mocked_run_git_command, "Refreshed podcast feed")


def test_refresh_podcast(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["refresh", "-p", "c/d/3"])
    assert result.exit_code == 0
    assert result.output == "Refreshing c/d/3\n"
    _assert_git_changes_commited(mocked_run_git_command, "Refreshed podcast feed")


def test_download_all_podcast_episodes(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["download"])
    assert result.exit_code == 0
    assert result.output == "Downloading b -> hello\n"
    _assert_git_changes_commited(mocked_run_git_command, "Downloaded podcast episodes")


def test_download_podcast_episodes(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["download", "-p", "b"])
    assert result.exit_code == 0
    assert result.output == "Downloading b -> hello\n"
    _assert_git_changes_commited(mocked_run_git_command, "Downloaded podcast episodes")


def test_error_handling_git_command_error(mocker, runner):
    mocker.patch(
        "pod_store.__main__.run_git_command",
        side_effect=GitCommandError("no such command zzz"),
    )

    result = runner.invoke(cli, ["git", "zzz"])
    assert result.exit_code == 0
    assert "Error running git command" in result.output


def test_error_handling_podcast_does_not_exist(runner):
    result = runner.invoke(cli, ["ls", "-p", "zzzz"])
    assert result.exit_code == 0
    assert "Podcast not found" in result.output


def test_error_handling_podcast_already_exists(runner):
    result = runner.invoke(cli, ["mv", "a/1", "b"])
    assert result.exit_code == 0
    assert "Podcast with title already exists" in result.output


def test_error_handling_store_already_exists(runner):
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Store already initialized" in result.output
