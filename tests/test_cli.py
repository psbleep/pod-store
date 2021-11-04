import os

import requests

import pytest
from click.testing import CliRunner

from pod_store.__main__ import cli

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
def runner():
    return CliRunner()


def test_add(runner):
    result = runner.invoke(cli, ["add", "hello", "https://www.hello.world/rss"])
    assert result.exit_code == 0


def test_download_all_new_podcast_episodes(runner):
    result = runner.invoke(cli, ["download"])
    assert result.exit_code == 0
    assert result.output == (
        f"Downloading: {TEST_OTHER_EPISODE_DOWNLOAD_PATH}.\n"
        f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}.\n"
    )


def test_download_single_podcast_new_episodes(runner):
    result = runner.invoke(cli, ["download", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}.\n"


def test_download_new_episodes_with_tag(runner):
    result = runner.invoke(cli, ["download", "-t", "bar"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_OTHER_EPISODE_DOWNLOAD_PATH}.\n"


def test_download_new_episodes_without_tag(runner):
    result = runner.invoke(cli, ["download", "--not-tagged", "-t", "bar"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}.\n"


def test_encrypt_store(runner):
    result = runner.invoke(cli, ["encrypt-store", "foo@bar.com", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store encrypted with GPG ID.\n")


def test_encrypt_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["encrypt-store", "foo@bar.com"], input="\n")
    assert result.exit_code == 1


def test_git_runs_git_command(mocker, runner):
    mocked_run_git_command = mocker.patch("pod_store.__main__.run_git_command")
    result = runner.invoke(cli, ["git", "push", "-u", "origin", "master"])
    assert result.exit_code == 0
    mocked_run_git_command.assert_called_with("push -u origin master")


def test_git_help_still_works(runner):
    result = runner.invoke(cli, ["git", "--help"])
    assert result.exit_code == 0
    assert "Run a `git` command" in result.output


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


def test_ls_podcasts(runner):
    result = runner.invoke(cli, ["ls"])
    assert result.exit_code == 0
    assert "farewell" in result.output


def test_ls_podcasts_verbose_mode(now_formatted, runner):
    result = runner.invoke(cli, ["ls", "--verbose"])
    assert result.exit_code == 0
    assert f"created at: {now_formatted}" in result.output


def test_ls_podcasts_with_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--new"])
    assert result.exit_code == 0
    assert "farewell" in result.output
    assert "other" not in result.output


def test_ls_podcasts_with_tag(runner):
    result = runner.invoke(cli, ["ls", "--all", "-t", "hello"])
    assert result.exit_code == 0
    assert "greetings" in result.output
    assert "other" not in result.output


def test_ls_podcasts_without_tag(runner):
    result = runner.invoke(cli, ["ls", "--all", "--not-tagged", "-t", "hello"])
    assert result.exit_code == 0
    assert "farewell" in result.output
    assert "greetings" not in result.output


def test_ls_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all"])
    assert result.exit_code == 0
    assert "0001" in result.output


def test_ls_episodes_verbose_mode(now_formatted, runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all", "--verbose"])
    assert result.exit_code == 0
    assert "id: aaa" in result.output


def test_ls_new_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--new"])
    assert result.exit_code == 0
    assert "0001" in result.output
    assert "0002" not in result.output


def test_ls_episodes_with_tag(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "--all", "-t", "foo"])
    assert result.exit_code == 0
    assert "0002" in result.output
    assert "0001" not in result.output


def test_ls_without_tag(runner):
    result = runner.invoke(
        cli, ["ls", "--episodes", "--all", "--not-tagged", "-t", "foo"]
    )
    assert result.exit_code == 0
    assert "0001" in result.output
    assert "0002" not in result.output


def test_ls_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "--episodes", "-p", "greetings", "--all"])
    assert result.exit_code == 0
    assert "0023" in result.output
    assert "0001" not in result.output


def test_mark_as_new_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["mark-as-new", "--bulk"])
    assert result.exit_code == 0
    assert "Marked as 'new': farewell" in result.output
    assert "Marked as 'new': greetings" in result.output


def test_mark_as_new_for_single_podcast(runner):
    result = runner.invoke(cli, ["mark-as-new", "-p", "farewell", "--bulk"])
    assert result.exit_code == 0
    assert "Marked as 'new': farewell" in result.output
    assert "Marked as 'new': greetings" not in result.output


def test_mark_as_new_interactive_mode(runner):
    result = runner.invoke(
        cli, ["mark-as-new", "-p", "farewell", "--interactive"], input="y\nn\n"
    )
    assert result.exit_code == 0
    assert "Marked as 'new': farewell" in result.output


def test_mark_as_old_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["mark-as-old", "--bulk"])
    assert result.exit_code == 0
    assert "Unmarked as 'new': farewell" in result.output
    assert "Unmarked as 'new': greetings" in result.output


def test_mark_as_old_for_single_podcast(runner):
    result = runner.invoke(cli, ["mark-as-old", "-p", "farewell", "--bulk"])
    assert result.exit_code == 0
    assert "Unmarked as 'new': farewell" in result.output
    assert "Unmarked as 'new': greetings" not in result.output


def test_mark_as_old_interactive_mode(runner):
    result = runner.invoke(
        cli, ["mark-as-old", "-p", "farewell", "--interactive"], input="y\nn\n"
    )
    assert result.exit_code == 0
    assert "Unmarked as 'new': farewell" in result.output


def test_mv(runner):
    result = runner.invoke(cli, ["mv", "farewell", "foowell"])
    assert result.exit_code == 0


def test_refresh_all_podcasts(runner):
    result = runner.invoke(cli, ["refresh"])
    assert result.exit_code == 0
    assert (
        result.output == "Refreshing farewell\nRefreshing other\nRefreshing greetings\n"
    )


def test_refresh_single_podcast(runner):
    result = runner.invoke(cli, ["refresh", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings\n"


def test_refresh_podcasts_with_tag(runner):
    result = runner.invoke(cli, ["refresh", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings\n"


def test_refresh_podcasts_without_tag(runner):
    result = runner.invoke(cli, ["refresh", "--not-tagged", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing farewell\nRefreshing other\n"


def test_refresh_podcast_times_out(mocked_requests_get, runner):
    mocked_requests_get.configure_mock(**{"side_effect": requests.ReadTimeout()})
    result = runner.invoke(cli, ["refresh", "-p", "greetings"])
    assert result.exit_code == 0
    assert "timed out" in result.output


def test_rm(runner):
    result = runner.invoke(cli, ["rm", "greetings", "--force"])
    assert result.exit_code == 0


def test_rm_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["rm", "greetings"], input="n\n")
    assert result.exit_code == 1


def test_tag_a_podcast(runner):
    result = runner.invoke(cli, ["tag", "greetings", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged as 'foobar': greetings.\n"


def test_tag_a_pocast_episode(runner):
    result = runner.invoke(cli, ["tag", "greetings", "--episode", "aaa", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged as 'foobar': greetings -> [0023] hello.\n"


def test_tag_episodes_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["tag-episodes", "foo", "--bulk"])
    assert result.exit_code == 0
    assert "Tagged as 'foo': farewell" in result.output
    assert "Tagged as 'foo': greetings" in result.output


def test_tag_episodes_for_single_podcast(runner):
    result = runner.invoke(cli, ["tag-episodes", "zozo", "-p", "greetings", "--bulk"])
    assert result.exit_code == 0
    assert "Tagged as 'zozo': farewell" not in result.output
    assert "Tagged as 'zozo': greetings" in result.output


def test_tag_episodes_interactive_mode(runner):
    result = runner.invoke(
        cli, ["tag-episodes", "foo", "--interactive"], input="n\ny\n"
    )
    assert result.exit_code == 0
    assert "Tagged as 'foo': farewell" not in result.output
    assert "Tagged as 'foo': greetings" in result.output


def test_unencrypt_store(runner):
    with open(TEST_GPG_ID_FILE_PATH, "w") as f:
        f.write("abc@xyz.com")
    result = runner.invoke(cli, ["unencrypt-store", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store was unencrypted.\n")


def test_unencrypt_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["unencrypt-store"], input="\n")
    assert result.exit_code == 1


def test_untag_a_podcast(runner):
    result = runner.invoke(cli, ["untag", "greetings", "hello"])
    assert result.exit_code == 0
    assert result.output == "Untagged as 'hello': greetings.\n"


def test_untag_single_pocast_episode(runner):
    result = runner.invoke(cli, ["untag", "greetings", "--episode", "aaa", "new"])
    assert result.exit_code == 0
    assert result.output == "Untagged as 'new': greetings -> [0023] hello.\n"


def test_untag_episodes_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["untag-episodes", "foo", "--bulk"])
    assert result.exit_code == 0
    assert "Untagged as 'foo': farewell" in result.output
    assert "Untagged as 'foo': greetings" in result.output


def test_untag_episodes_for_single_podcast(runner):
    result = runner.invoke(cli, ["untag-episodes", "foo", "-p", "greetings", "--bulk"])
    assert result.exit_code == 0
    assert "Untagged as 'foo': farewell" not in result.output
    assert "Untagged as 'foo': greetings" in result.output


def test_untag_episodes_interactive_mode(runner):
    result = runner.invoke(
        cli, ["untag-episodes", "foo", "--interactive"], input="n\ny\nn\n"
    )
    assert result.exit_code == 0
    assert "Untagged as 'foo': farewell" not in result.output
    assert "Untagged as 'foo': greetings" in result.output
