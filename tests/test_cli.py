from unittest.mock import Mock, call

import pytest
from click.testing import CliRunner

from pod_store.__main__ import cli
from pod_store.exc import GitCommandError

from . import TEST_PODCAST_DOWNLOADS_PATH, TEST_STORE_PATH


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.cmd_decorators.run_git_command")


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
        f"Podcast episodes will be downloaded to {TEST_PODCAST_DOWNLOADS_PATH}\n"
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


def test_add(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["add", "hello", "https://www.hello.world/rss"])
    assert result.exit_code == 0

    _assert_git_changes_commited(mocked_run_git_command, "Added podcast: hello.")


def test_download_all_podcast_episodes(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["download"])
    assert result.exit_code == 0
    assert result.output == "Downloading greetings -> hello\n"
    _assert_git_changes_commited(mocked_run_git_command, "Downloaded all new episodes.")


def test_download_single_podcast_episodes(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["download", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == "Downloading greetings -> hello\n"
    _assert_git_changes_commited(
        mocked_run_git_command, "Downloaded greetings new episodes."
    )


def test_ls_all_podcasts(runner):
    result = runner.invoke(cli, ["ls", "--all"])
    assert result.exit_code == 0
    assert result.output == "farewell \ngreetings [1]\n"


def test_ls_podcasts_with_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--new"])
    assert result.exit_code == 0
    assert result.output == "greetings [1]\n"


def test_ls_all_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--all"])
    assert result.exit_code == 0
    assert result.output == "greetings\n\n[0023] hello \n[0011] goodbye [X]\n"


def test_ls_new_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--new"])
    assert result.exit_code == 0
    assert result.output == "greetings\n\n[0023] hello \n"


def test_ls_all_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all"])
    assert result.exit_code == 0
    assert result.output == "greetings\n\n[0023] hello \n[0011] goodbye [X]\n"


def test_ls_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--new"])
    assert result.exit_code == 0
    assert result.output == "greetings\n\n[0023] hello \n"


def test_mark_interactive_marks_when_confirmed(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["mark", "--interactive"], input="y\n")
    assert result.exit_code == 0
    assert result.output.endswith("Marking greetings -> [0023] hello\n")
    _assert_git_changes_commited(mocked_run_git_command, "Marked all podcast episodes.")


def test_mark_interactive_does_not_mark_when_not_confirmed(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["mark", "--interactive"], input="n\n")
    assert result.exit_code == 0
    assert "Marking greetings" not in result.output
    _assert_git_changes_commited(mocked_run_git_command, "Marked all podcast episodes.")


def test_mark_bulk(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["mark", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith("Marking greetings -> [0023] hello\n")
    _assert_git_changes_commited(mocked_run_git_command, "Marked all podcast episodes.")


def test_mark_single_podcast_generates_correct_commit_message(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["mark", "-p", "farewell"])
    assert result.exit_code == 0
    _assert_git_changes_commited(
        mocked_run_git_command, "Marked farewell podcast episodes."
    )


def test_mv(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["mv", "farewell", "foowell"])
    assert result.exit_code == 0
    _assert_git_changes_commited(
        mocked_run_git_command, "Renamed podcast: farewell -> foowell"
    )


def test_refresh_all_podcasts(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["refresh"])
    assert result.exit_code == 0
    assert result.output == "Refreshing farewell\nRefreshing greetings\n"
    _assert_git_changes_commited(mocked_run_git_command, "Refreshed all podcast feed.")


def test_refresh_single_podcast(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["refresh", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings\n"
    _assert_git_changes_commited(
        mocked_run_git_command, "Refreshed greetings podcast feed."
    )


def test_rm(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["rm", "greetings"])
    assert result.exit_code == 0
    _assert_git_changes_commited(mocked_run_git_command, "Removed podcast: greetings.")


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
    result = runner.invoke(cli, ["mv", "greetings", "farewell"])
    assert result.exit_code == 0
    assert "Podcast with title already exists" in result.output


def test_error_handling_store_already_exists(runner):
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Store already initialized" in result.output
