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

TEST_OTHER_EPISODE_DOWNLOAD_PATH = os.path.join(
    TEST_PODCAST_DOWNLOADS_PATH, "farewell/0001-gone.mp3"
)


@pytest.fixture
def mocked_git_decorator_command(mocker):
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


def test_encrypt_store(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["encrypt-store", "foo@bar.com", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store encrypted with GPG ID.\n")
    _assert_git_changes_commited(mocked_git_decorator_command, "Encrypted the store.")


def test_encrypt_aborts_if_not_confirmed(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["encrypt-store", "foo@bar.com"], input="\n")
    assert result.exit_code == 1
    mocked_git_decorator_command.assert_not_called()


def test_unencrypt_store(mocked_git_decorator_command, runner):
    with open(TEST_GPG_ID_FILE_PATH, "w") as f:
        f.write("abc@xyz.com")
    result = runner.invoke(cli, ["unencrypt-store", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store was unencrypted.\n")
    _assert_git_changes_commited(mocked_git_decorator_command, "Unencrypted the store.")


def test_unencrypt_aborts_if_not_confirmed(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["unencrypt-store"], input="\n")
    assert result.exit_code == 1
    mocked_git_decorator_command.assert_not_called()


def test_add(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["add", "hello", "https://www.hello.world/rss"])
    assert result.exit_code == 0
    _assert_git_changes_commited(mocked_git_decorator_command, "Added podcast: hello.")


def test_download_all_new_podcast_episodes(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["download"])
    assert result.exit_code == 0
    assert result.output == (
        f"Downloading: {TEST_OTHER_EPISODE_DOWNLOAD_PATH}\n"
        f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}\n"
    )
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Downloaded all new episodes."
    )


def test_download_single_podcast_new_episodes(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["download", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Downloaded greetings new episodes."
    )


def test_download_new_episodes_with_tag(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["download", "-t", "bar"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_OTHER_EPISODE_DOWNLOAD_PATH}\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Downloaded all new episodes."
    )


def test_download_new_episodes_without_tag(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["download", "--not-tagged", "-t", "bar"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Downloaded all new episodes."
    )


def test_ls_all_podcasts(runner):
    result = runner.invoke(cli, ["ls", "--all"])
    assert result.exit_code == 0
    assert result.output == "farewell [1]\nother\ngreetings [1] -> hello\n"


def test_ls_podcasts_with_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--new"])
    assert result.exit_code == 0
    assert result.output == "farewell [1]\ngreetings [1] -> hello\n"


def test_ls_podcasts_with_tag(runner):
    result = runner.invoke(cli, ["ls", "--all", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "greetings [1] -> hello\n"


def test_ls_podcasts_without_tag(runner):
    result = runner.invoke(cli, ["ls", "--all", "--not-tagged", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "farewell [1]\nother\n"


def test_ls_all_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all"])
    assert result.exit_code == 0
    assert result.output == (
        "farewell\n"
        "[0001] gone: 'all gone' -> new, bar\n\n"
        "greetings\n"
        "[0023] hello: 'hello world' -> new\n"
        "[0011] goodbye: 'goodbye world' [X] -> foo\n"
    )


def test_ls_episodes_with_verbose_flag(now, runner):
    now_formatted = now.isoformat()
    result = runner.invoke(cli, ["ls", "--episodes", "--all", "--verbose"])
    assert result.exit_code == 0
    expected = """farewell
[0001] gone
tags: new, bar
all gone (longer)

greetings
[0023] hello
tags: new
hello world (longer)

[0011] goodbye
tags: foo
downloaded at: {}
goodbye world (longer)
""".format(
        now_formatted
    )
    assert result.output == expected


def test_ls_all_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--new"])
    assert result.exit_code == 0
    assert result.output == (
        "farewell\n"
        "[0001] gone: 'all gone' -> new, bar\n\n"
        "greetings\n"
        "[0023] hello: 'hello world' -> new\n"
    )


def test_ls_all_episodes_with_tag(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all", "-t", "foo"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0011] goodbye: 'goodbye world' [X] -> foo\n"


def test_ls_all_episodes_without_tag(runner):
    result = runner.invoke(
        cli, ["ls", "--episodes", "--all", "--not-tagged", "-t", "foo"]
    )
    assert result.exit_code == 0
    assert result.output == (
        "farewell\n"
        "[0001] gone: 'all gone' -> new, bar\n\n"
        "greetings\n"
        "[0023] hello: 'hello world' -> new\n"
    )


def test_ls_all_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--all"])
    assert result.exit_code == 0
    assert result.output == (
        "greetings\n"
        "[0023] hello: 'hello world' -> new\n"
        "[0011] goodbye: 'goodbye world' [X] -> foo\n"
    )


def test_ls_new_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--new"])
    assert result.exit_code == 0
    assert result.output == "greetings\n[0023] hello: 'hello world' -> new\n"


def test_mark_as_old_works_as_alias_for_untag_new_episodes_command(
    mocked_git_decorator_command, runner
):
    result = runner.invoke(cli, ["mark-as-old", "-p", "greetings", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith("Untagged greetings -> [0023] hello\n")
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Untagged greetings podcast episodes: new."
    )


def test_mv(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["mv", "farewell", "foowell"])
    assert result.exit_code == 0
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Renamed podcast: farewell -> foowell."
    )


def test_refresh_all_podcasts(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["refresh"])
    assert result.exit_code == 0
    assert (
        result.output == "Refreshing farewell\nRefreshing other\nRefreshing greetings\n"
    )
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Refreshed all podcast feed."
    )


def test_refresh_single_podcast(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["refresh", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Refreshed greetings podcast feed."
    )


def test_refresh_podcasts_with_tag(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["refresh", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Refreshed all podcast feed."
    )


def test_refresh_podcasts_without_tag(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["refresh", "--not-tagged", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing farewell\nRefreshing other\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Refreshed all podcast feed."
    )


def test_rm(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["rm", "greetings", "--force"])
    assert result.exit_code == 0
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Removed podcast: greetings."
    )


def test_rm_aborts_if_not_confirmed(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["rm", "greetings"], input="n\n")
    assert result.exit_code == 1
    mocked_git_decorator_command.assert_not_called()


def test_tag_single_podcast(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["tag", "greetings", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged greetings -> foobar.\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Tagged greetings -> foobar."
    )


def test_tag_single_pocast_episode(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["tag", "greetings", "--episode", "aaa", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged greetings, episode aaa -> foobar.\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Tagged greetings, episode aaa -> foobar."
    )


def test_untag_single_podcast(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["untag", "greetings", "hello"])
    assert result.exit_code == 0
    assert result.output == "Untagged greetings -> hello.\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Untagged greetings -> hello."
    )


def test_untag_single_pocast_episode(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["untag", "greetings", "--episode", "aaa", "new"])
    assert result.exit_code == 0
    assert result.output == "Untagged greetings, episode aaa -> new.\n"
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Untagged greetings, episode aaa -> new."
    )


def test_tag_episodes_for_all_podcasts_generates_correct_commit_message(
    mocked_git_decorator_command, runner
):
    runner.invoke(cli, ["tag-episodes", "zozo", "--bulk"])
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Tagged all podcast episodes: zozo."
    )


def test_tag_episodes_for_single_podcast_generates_correct_commit_message(
    mocked_git_decorator_command, runner
):
    runner.invoke(cli, ["tag-episodes", "zozo", "-p", "greetings", "--bulk"])
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Tagged greetings podcast episodes: zozo."
    )


def test_tag_episodes_interactive_mode_tags_based_on_confirmation(runner):
    result = runner.invoke(
        cli, ["tag-episodes", "foo", "--interactive"], input="n\ny\n"
    )
    assert result.exit_code == 0
    assert "Tagged greetings -> [0023] hello" in result.output
    assert "Tagged farewell" not in result.output


def test_tag_episodes_interactive_mode_switches_to_bulk_mode_when_prompted_by_user(
    runner,
):
    result = runner.invoke(
        cli, ["tag-episodes", "zazaza", "--interactive"], input="n\nb\n"
    )
    assert result.exit_code == 0
    assert "Tagged farewell" not in result.output
    assert "Tagged greetings -> [0023] hello" in result.output
    assert "Tagged greetings -> [0011] goodbye" in result.output


def test_tag_episodes_interactive_mode_aborts_when_quit(runner):
    result = runner.invoke(
        cli, ["tag-episodes", "foo", "--interactive"], input="n\nq\n"
    )
    assert result.exit_code == 1
    assert "Aborted!" in result.output
    assert "Tagged" not in result.output


def test_tag_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["tag-episodes", "foo", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith(
        "Tagged farewell -> [0001] gone\nTagged greetings -> [0023] hello\n"
    )


def test_untag_episodes_for_all_podcasts_generates_correct_commit_message(
    mocked_git_decorator_command, runner
):
    runner.invoke(cli, ["untag-episodes", "zozo", "--bulk"])
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Untagged all podcast episodes: zozo."
    )


def test_untag_episodes_for_single_podcast_generates_correct_commit_message(
    mocked_git_decorator_command, runner
):
    runner.invoke(cli, ["untag-episodes", "zozo", "-p", "greetings", "--bulk"])
    _assert_git_changes_commited(
        mocked_git_decorator_command, "Untagged greetings podcast episodes: zozo."
    )


def test_untag_episodes_interactive_mode_untags_based_on_confirmation(runner):
    result = runner.invoke(
        cli, ["untag-episodes", "new", "--interactive"], input="n\ny\n"
    )
    assert result.exit_code == 0
    assert "Untagged greetings -> [0023] hello" in result.output
    assert "Untagged farewell" not in result.output


def test_untag_episodes_interactive_aborts_when_quit(runner):
    result = runner.invoke(
        cli, ["untag-episodes", "new", "--interactive"], input="n\nq\n"
    )
    assert result.exit_code == 1
    assert "Aborted!" in result.output
    assert "Untagged" not in result.output


def test_untag_episodes_bulk(mocked_git_decorator_command, runner):
    result = runner.invoke(cli, ["untag-episodes", "new", "--bulk"])
    assert result.exit_code == 0
    assert result.output.endswith(
        "Untagged farewell -> [0001] gone\nUntagged greetings -> [0023] hello\n"
    )


def test_git_runs_git_command(mocker, runner):
    mocked_run_git_command = mocker.patch("pod_store.__main__.run_git_command")
    result = runner.invoke(cli, ["git", "push", "-u", "origin", "master"])
    assert result.exit_code == 0
    mocked_run_git_command.assert_called_with("push -u origin master")


def test_git_help_still_works(runner):
    result = runner.invoke(cli, ["git", "--help"])
    assert result.exit_code == 0
    assert "Run a `git` command" in result.output


def test_git_add_and_commit_decorated_commands_work_if_git_is_not_set_up(
    start_with_no_store, mocked_git_decorator_command, runner
):
    runner.invoke(cli, ["init", "--no-git"])
    result = runner.invoke(cli, ["add", "not-git-tracked", "http://fake.url.com/rss"])
    assert result.exit_code == 0
    mocked_git_decorator_command.assert_not_called()


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
