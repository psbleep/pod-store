import os
from unittest.mock import Mock, call

import pytest
from click.testing import CliRunner

from pod_store.__main__ import cli
from pod_store.exc import GPGCommandError, ShellCommandError

from . import (
    TEST_GPG_ID_FILE_PATH,
    TEST_PODCAST_DOWNLOADS_PATH,
    TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
    TEST_STORE_PATH,
)

TEST_EPISODE_DOWNLOAD_PATH = os.path.join(
    TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0023-hello.mp3"
)


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.commands.decorators.run_git_command")


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
    result = runner.invoke(cli, ["init", "-u", "https://git.foo.bar/pod-store.git"])
    assert result.exit_code == 0
    assert result.output.endswith(
        "Git tracking enabled: https://git.foo.bar/pod-store.git\n"
    )


def test_init_with_gpg_id(start_with_no_store, runner):
    result = runner.invoke(cli, ["init", "--no-git", "-g", "foo@bar.com"])
    assert result.exit_code == 0
    assert result.output.endswith("GPG ID set for store encryption.\n")


def test_encrypt_store(runner):
    result = runner.invoke(cli, ["encrypt-store", "foo@bar.com", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store encrypted with GPG ID.\n")


def test_encrypt_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["encrypt-store", "foo@bar.com"], input="\n")
    assert result.exit_code == 1


def test_unencrypt_store(runner):
    with open(TEST_GPG_ID_FILE_PATH, "w") as f:
        f.write("abc@xyz.com")
    result = runner.invoke(cli, ["unencrypt-store", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store was unencrypted.\n")


def test_unencrypt_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["unencrypt-store"], input="\n")
    assert result.exit_code == 1


def test_add(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["add", "hello", "https://www.hello.world/rss"])
    assert result.exit_code == 0

    _assert_git_changes_commited(mocked_run_git_command, "Added podcast: hello.")


def test_download_all_podcast_episodes(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["download"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}\n"
    _assert_git_changes_commited(mocked_run_git_command, "Downloaded all new episodes.")


def test_download_single_podcast_episodes(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["download", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}\n"
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


def test_ls_podcasts_with_tag(runner):
    result = runner.invoke(cli, ["ls", "--all", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "greetings [1]\n"


def test_ls_podcasts_without_tag(runner):
    result = runner.invoke(cli, ["ls", "--all", "--not-tagged", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "farewell \n"


def test_ls_all_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--all"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0023] hello \n[0011] goodbye [X]\n\n"


def test_ls_new_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--new"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0023] hello \n\n"


def test_ls_all_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0023] hello \n[0011] goodbye [X]\n\n"


def test_ls_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--new"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0023] hello \n\n"


def test_ls_episodes_with_tag(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all", "-t", "foo"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0011] goodbye [X]\n\n"


def test_ls_episodes_without_tag(runner):
    result = runner.invoke(
        cli, ["ls", "--episodes", "--all", "--not-tagged", "-t", "foo"]
    )
    assert result.exit_code == 0
    assert result.output == "greetings\n[0023] hello \n\n"


def test_mark_as_old_works_as_alias_for_untag_new_episodes_command(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["mark-as-old", "-p", "greetings", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith("Untagged greetings -> [0023] hello\n")


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


def test_refresh_with_tag(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["refresh", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings\n"
    _assert_git_changes_commited(mocked_run_git_command, "Refreshed all podcast feed.")


def test_refresh_without_tag(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["refresh", "--not-tagged", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing farewell\n"
    _assert_git_changes_commited(mocked_run_git_command, "Refreshed all podcast feed.")


def test_rm(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["rm", "greetings", "--force"])
    assert result.exit_code == 0
    _assert_git_changes_commited(mocked_run_git_command, "Removed podcast: greetings.")


def test_rm_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["rm", "greetings"], input="n\n")
    assert result.exit_code == 1


def test_tag_single_podcast(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["tag", "greetings", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged greetings -> foobar.\n"
    _assert_git_changes_commited(mocked_run_git_command, "Tagged greetings -> foobar.")


def test_tag_single_pocast_episode(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["tag", "greetings", "--episode", "aaa", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged greetings, episode aaa -> foobar.\n"
    _assert_git_changes_commited(
        mocked_run_git_command, "Tagged greetings, episode aaa -> foobar."
    )


def test_untag_single_podcast(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["untag", "greetings", "hello"])
    assert result.exit_code == 0
    assert result.output == "Untagged greetings -> hello.\n"
    _assert_git_changes_commited(mocked_run_git_command, "Untagged greetings -> hello.")


def test_untag_single_pocast_episode(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["untag", "greetings", "--episode", "aaa", "new"])
    assert result.exit_code == 0
    assert result.output == "Untagged greetings, episode aaa -> new.\n"
    _assert_git_changes_commited(
        mocked_run_git_command, "Untagged greetings, episode aaa -> new."
    )


def test_tag_episodes_interactive_mode_tags_episode_when_confirmed(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["tag-episodes", "new", "--interactive"], input="y\n")
    assert result.exit_code == 0
    assert result.output.endswith("Tagged greetings -> [0011] goodbye\n")
    _assert_git_changes_commited(
        mocked_run_git_command, "Tagged all podcast episodes: new."
    )


def test_tag_episodes_interactive_mode_does_not_tag_episode_when_not_confirmed(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["tag-episodes", "new", "--interactive"], input="n\n")
    assert result.exit_code == 0
    assert "Tagged" not in result.output


def test_tag_episodes_interactive_mode_aborts_when_quit(runner):
    result = runner.invoke(cli, ["tag-episodes", "foo", "--interactive"], input="q\n")
    assert result.exit_code == 1
    assert "Aborted!" in result.output
    assert "Tagged" not in result.output


def test_tag_episodes_bulk_mode(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["tag-episodes", "new", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith("Tagged greetings -> [0011] goodbye\n")


def test_tag_episodes_single_podcast_generates_correct_commit_message(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["tag-episodes", "new", "-p", "greetings", "--bulk"])
    assert result.exit_code == 0
    _assert_git_changes_commited(
        mocked_run_git_command, "Tagged greetings podcast episodes: new."
    )


def test_untag_episodes_interactive_untags_when_confirmed(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["untag-episodes", "new", "--interactive"], input="y\n")
    assert result.exit_code == 0
    assert result.output.endswith("Untagged greetings -> [0023] hello\n")
    _assert_git_changes_commited(
        mocked_run_git_command, "Untagged all podcast episodes: new."
    )


def test_untag_episodes_interactive_does_not_untag_when_not_confirmed(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["untag-episodes", "new", "--interactive"], input="n\n")
    assert result.exit_code == 0
    assert "Untagged" not in result.output


def test_untag_episodes_interactive_aborts_when_quit(runner):
    result = runner.invoke(cli, ["untag-episodes", "new", "--interactive"], input="q\n")
    assert result.exit_code == 1
    assert "Aborted!" in result.output
    assert "Untagged" not in result.output


def test_untag_episodes_bulk(mocked_run_git_command, runner):
    result = runner.invoke(cli, ["untag-episodes", "new", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith("Untagged greetings -> [0023] hello\n")


def test_untag_episodes_single_podcast_generates_correct_commit_message(
    mocked_run_git_command, runner
):
    result = runner.invoke(cli, ["untag-episodes", "new", "-p", "greetings", "--bulk"])
    assert result.exit_code == 0
    _assert_git_changes_commited(
        mocked_run_git_command, "Untagged greetings podcast episodes: new."
    )


def test_git_add_and_commit_decorated_commands_work_if_git_is_not_set_up(
    start_with_no_store, mocked_run_git_command, runner
):
    runner.invoke(cli, ["init", "--no-git"])
    result = runner.invoke(cli, ["add", "not-git-tracked", "http://fake.url.com/rss"])
    assert result.exit_code == 0
    mocked_run_git_command.assert_not_called()


def test_error_handling_gpg_command_error(mocker, runner):
    mocker.patch(
        "pod_store.__main__.run_git_command",
        side_effect=GPGCommandError("you are hacked"),
    )

    result = runner.invoke(cli, ["git", "zzz"])
    assert result.exit_code == 1
    assert (
        "Error encountered when running GPG commands: you are hacked." in result.output
    )


def test_error_handling_no_podcasts_found(runner):
    result = runner.invoke(cli, ["ls", "-p", "zzzz"])
    assert result.exit_code == 1
    assert "No podcasts found" in result.output


def test_error_handling_podcast_already_exists(runner):
    result = runner.invoke(cli, ["mv", "greetings", "farewell"])
    assert result.exit_code == 1
    assert "Podcast with title already exists" in result.output


def test_error_handling_shell_command_error(mocker, runner):
    mocker.patch(
        "pod_store.__main__.run_git_command",
        side_effect=ShellCommandError("no such command zzz"),
    )

    result = runner.invoke(cli, ["git", "zzz"])
    assert result.exit_code == 1
    assert "Error running shell command" in result.output


def test_error_handling_store_already_exists(runner):
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "Store already initialized" in result.output
