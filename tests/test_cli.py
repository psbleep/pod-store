import os

import pytest
import requests
from click.testing import CliRunner

from pod_store import DEFAULT_ENCRYPTED_STORE_FILE_NAME
from pod_store.__main__ import cli

from . import (
    TEST_GPG_ID_FILE_PATH,
    TEST_PODCAST_DOWNLOADS_PATH,
    TEST_PODCAST_EPISODE_DOWNLOADS_PATH,
    TEST_STORE_FILE_PATH,
    TEST_STORE_PATH,
)

TEST_EPISODE_DOWNLOAD_PATH = os.path.join(
    TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0023-hello.mp3"
)

OTHER_TEST_PODCAST_EPISODE_DOWNLOADS_PATH = os.path.join(
    TEST_PODCAST_DOWNLOADS_PATH, "farewell"
)

OTHER_TEST_EPISODE_DOWNLOAD_PATH = os.path.join(
    OTHER_TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0001-gone.mp3"
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def timed_out_request(mocked_requests_get):
    mocked_requests_get.configure_mock(**{"side_effect": requests.ConnectTimeout()})


def test_add(runner):
    result = runner.invoke(cli, ["add", "hello", "https://www.hello.world/rss"])
    assert result.exit_code == 0


def test_download_all_new_podcast_episodes(runner):
    result = runner.invoke(cli, ["download"])
    assert result.exit_code == 0
    assert result.output == (
        f"Downloading: {OTHER_TEST_EPISODE_DOWNLOAD_PATH}.\n\n"
        f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}.\n\n"
    )


def test_download_episodes_for_podcasts_with_tag(runner):
    result = runner.invoke(cli, ["download", "-pt", "hello"])
    assert result.exit_code == 0
    assert TEST_PODCAST_EPISODE_DOWNLOADS_PATH in result.output
    assert OTHER_TEST_PODCAST_EPISODE_DOWNLOADS_PATH not in result.output


def test_download_episodes_for_podcasts_without_tag(runner):
    result = runner.invoke(cli, ["download", "-up", "hello"])
    assert result.exit_code == 0
    assert OTHER_TEST_PODCAST_EPISODE_DOWNLOADS_PATH in result.output
    assert TEST_PODCAST_EPISODE_DOWNLOADS_PATH not in result.output


def test_download_single_podcast_new_episodes(runner):
    result = runner.invoke(cli, ["download", "-p", "greetings"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}.\n\n"


def test_download_single_episode(runner):
    download_path = os.path.join(
        TEST_PODCAST_EPISODE_DOWNLOADS_PATH, "0011-goodbye.mp3"
    )
    # Tests against an episode that is not tagged as 'new', to verify that it will
    # still be downloaded if it is specifically chosen by the user.
    result = runner.invoke(cli, ["download", "-p", "greetings", "-e", "11"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {download_path}.\n\n"


def test_download_episodes_with_tag(runner):
    result = runner.invoke(cli, ["download", "-t", "bar"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {OTHER_TEST_EPISODE_DOWNLOAD_PATH}.\n\n"


def test_download_episodes_without_tag(runner):
    result = runner.invoke(cli, ["download", "-u", "bar"])
    assert result.exit_code == 0
    assert result.output == f"Downloading: {TEST_EPISODE_DOWNLOAD_PATH}.\n\n"


def test_download_times_out(timed_out_request, runner):
    result = runner.invoke(cli, ["download", "-p", "greetings"])
    assert result.exit_code == 0
    assert "error" in result.output.lower()


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
        f"Store created: {TEST_STORE_FILE_PATH}\n"
        f"Podcast episodes will be downloaded to {TEST_PODCAST_DOWNLOADS_PATH}\n"
    )


def test_init_with_git(start_with_no_store, runner):
    result = runner.invoke(cli, ["init", "--git"])
    assert result.exit_code == 0
    assert result.output.endswith(
        "Git tracking enabled: no remote repo specified. "
        "You can manually add one later.\n"
    )


def test_init_with_git_url(
    mocked_git_clone_with_store_file, start_with_no_store, runner
):
    def _create_store_file(*args, **kwargs):
        os.makedirs(TEST_STORE_PATH)
        with open(TEST_STORE_FILE_PATH, "w") as f:
            f.write("")

    result = runner.invoke(cli, ["init", "-u", "https://git.foo.bar/pod-store.git"])
    assert result.exit_code == 0
    assert "take a minute" in result.output
    assert result.output.endswith(
        "Git tracking enabled: https://git.foo.bar/pod-store.git\n"
    )


def test_init_with_gpg_id(start_with_no_store, runner):
    encrypted_store_file_path = os.path.join(
        TEST_STORE_PATH, DEFAULT_ENCRYPTED_STORE_FILE_NAME
    )
    result = runner.invoke(cli, ["init", "--no-git", "-g", "foo@bar.com"])
    assert result.exit_code == 0
    assert encrypted_store_file_path in result.output
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
    result = runner.invoke(cli, ["ls", "--all", "-u", "hello"])
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
    result = runner.invoke(cli, ["ls", "--episodes", "--all", "-u", "foo"])
    assert result.exit_code == 0
    assert "0001" in result.output
    assert "0002" not in result.output


def test_ls_podcast_episodes(runner):
    result = runner.invoke(cli, ["ls", "-p", "greetings", "--all"])
    assert result.exit_code == 0
    assert "0023" in result.output
    assert "0001" not in result.output


def test_ls_single_podcast_episode(runner):
    # Test against an episode not marked as 'new' to verify that the new/not-new flag
    # is ignored in cases where the user is specifying a single episode.
    result = runner.invoke(cli, ["ls", "-p", "greetings", "-e", "11"])
    assert result.exit_code == 0
    assert "0011" in result.output
    assert "0023" not in result.output  # does not show other podcast episode data


def test_mark_as_new_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["mark-as-new", "--force", "--bulk"])
    assert result.exit_code == 0
    assert "Marked as new: farewell" in result.output
    assert "Marked as new: greetings" in result.output


def test_mark_as_new_reverse_order(runner):
    result = runner.invoke(cli, ["mark-as-new", "--reverse", "--force", "--bulk"])
    assert result.exit_code == 0
    assert result.output.index("greetings") < result.output.index("farewell")


def test_mark_as_new_for_single_podcast(runner):
    result = runner.invoke(cli, ["mark-as-new", "--force", "--bulk", "-p", "farewell"])
    assert result.exit_code == 0
    assert "Marked as new: farewell" in result.output
    assert "Marked as new: greetings" not in result.output


def test_mark_as_new_episode_range_for_podcast(runner):
    result = runner.invoke(
        cli,
        [
            "mark-as-new",
            "--force",
            "--bulk",
            "--start",
            "11",
            "--end",
            "22",
            "-p",
            "greetings",
        ],
    )
    assert result.exit_code == 0
    assert "Marked as new: greetings" in result.output
    assert "011" in result.output
    assert "023" not in result.output


def test_mark_as_new_interactive_mode(runner):
    result = runner.invoke(
        cli, ["mark-as-new", "-p", "farewell", "--interactive"], input="y\nn\n"
    )
    assert result.exit_code == 0
    assert "Marked as new: farewell" in result.output


def test_mark_as_old_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["mark-as-old", "--force", "--bulk"])
    assert result.exit_code == 0
    assert "Unmarked as new: farewell" in result.output
    assert "Unmarked as new: greetings" in result.output


def test_mark_as_old_reverse_order(runner):
    result = runner.invoke(cli, ["mark-as-old", "--reverse", "--force", "--bulk"])
    assert result.exit_code == 0
    assert result.output.index("greetings") < result.output.index("farewell")


def test_mark_as_old_episode_range_for_podcast(runner):
    result = runner.invoke(
        cli,
        [
            "mark-as-old",
            "--force",
            "--bulk",
            "--start",
            "11",
            "--end",
            "23",
            "-p",
            "greetings",
        ],
    )
    assert result.exit_code == 0
    assert "Unmarked as new: greetings" in result.output
    assert "023" in result.output
    assert "011" not in result.output


def test_mark_as_old_for_single_podcast(runner):
    result = runner.invoke(cli, ["mark-as-old", "--force", "--bulk", "-p", "farewell"])
    assert result.exit_code == 0
    assert "Unmarked as new: farewell" in result.output
    assert "Unmarked as new: greetings" not in result.output


def test_mark_as_old_interactive_mode(runner):
    result = runner.invoke(
        cli, ["mark-as-old", "-p", "farewell", "--interactive"], input="y\nn\n"
    )
    assert result.exit_code == 0
    assert "Unmarked as new: farewell" in result.output


def test_mv(runner):
    result = runner.invoke(cli, ["mv", "farewell", "foowell"])
    assert result.exit_code == 0


def test_refresh_all_podcasts_ignores_inactive_podcasts(runner):
    result = runner.invoke(cli, ["refresh"])
    assert result.exit_code == 0
    assert result.output == "Refreshing farewell.\nRefreshing greetings.\n"


def test_refresh_single_podcast_will_force_refresh_of_inactive_podcast(runner):
    result = runner.invoke(cli, ["refresh", "-p", "other"])
    assert result.exit_code == 0
    assert result.output == "Refreshing other.\n"


def test_refresh_podcasts_with_tag(runner):
    result = runner.invoke(cli, ["refresh", "-t", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing greetings.\n"


def test_refresh_podcasts_without_tag(runner):
    result = runner.invoke(cli, ["refresh", "-u", "hello"])
    assert result.exit_code == 0
    assert result.output == "Refreshing farewell.\n"


def test_refresh_podcast_encounters_error(timed_out_request, runner):
    result = runner.invoke(cli, ["refresh", "-p", "greetings"])
    assert result.exit_code == 0
    assert "error" in result.output.lower()


def test_rm(runner):
    result = runner.invoke(cli, ["rm", "greetings", "--force"])
    assert result.exit_code == 0


def test_rm_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["rm", "greetings"], input="n\n")
    assert result.exit_code == 1


def test_set_active(runner):
    result = runner.invoke(cli, ["set-active", "other"])
    assert result.exit_code == 0


def test_set_inactive(runner):
    result = runner.invoke(cli, ["set-inactive", "greetings"])
    assert result.exit_code == 0


def test_tag_all_episodes_bulk_mode(runner):
    result = runner.invoke(cli, ["tag", "-t", "foo", "--force", "--bulk"])
    assert result.exit_code == 0
    assert "Tagged as foo: farewell" in result.output
    assert "Tagged as foo: greetings" in result.output


def test_tag_reverse_order(runner):
    result = runner.invoke(cli, ["tag", "-t", "foo", "--reverse", "--force", "--bulk"])
    assert result.exit_code == 0
    assert result.output.index("greetings") < result.output.index("farewell")


def test_tag_episodes_for_single_podcast(runner):
    result = runner.invoke(
        cli, ["tag", "-t", "zozo", "--force", "--bulk", "-p", "greetings"]
    )
    assert result.exit_code == 0
    assert "Tagged as zozo: farewell" not in result.output
    assert "Tagged as zozo: greetings" in result.output


def test_tag_episode_range_for_podcast(runner):
    result = runner.invoke(
        cli,
        [
            "tag",
            "-t",
            "zozo",
            "--force",
            "--bulk",
            "-p",
            "greetings",
            "--start",
            "12",
            "--end",
            "23",
        ],
    )
    assert result.exit_code == 0
    assert "Tagged as zozo: greetings" in result.output
    assert "023" in result.output
    assert "012" not in result.output


def test_tag_episodes_interactive_mode(runner):
    result = runner.invoke(cli, ["tag", "-t", "foo", "--interactive"], input="n\ny\n")
    assert result.exit_code == 0
    assert "Tagged as foo: farewell" not in result.output
    assert "Tagged as foo: greetings" in result.output


def test_tag_all_podcasts_bulk_mode(runner):
    result = runner.invoke(cli, ["tag", "-t", "zoo", "--podcasts", "--force", "--bulk"])
    assert result.exit_code == 0
    assert "Tagged as zoo: farewell" in result.output
    assert "Tagged as zoo: other" in result.output
    assert "Tagged as zoo: greetings" in result.output


def test_tag_podcasts_interactive_mode(runner):
    result = runner.invoke(
        cli, ["tag", "-t", "zoo", "--podcasts", "--interactive"], input="n\ny\nn\n"
    )
    assert result.exit_code == 0
    assert "Tagged as zoo: farewell" not in result.output
    assert "Tagged as zoo: other" in result.output
    assert "Tagged as zoo: greetings" not in result.output


def test_tag_single_podcast(runner):
    result = runner.invoke(cli, ["tag", "--bulk", "-p", "greetings", "-t", "foobar"])
    assert result.exit_code == 0
    assert result.output == "Tagged as foobar: greetings.\n"


def test_tag_single_episode(runner):
    result = runner.invoke(
        cli, ["tag", "--bulk", "-p", "greetings", "--episode", "023", "-t", "foobar"]
    )
    assert result.exit_code == 0
    assert result.output == "Tagged as foobar: greetings -> [0023] hello.\n"


def test_tag_with_untag_flag(runner):
    result = runner.invoke(
        cli, ["tag", "-t", "foo", "--untag", "--episodes", "--bulk", "--force"]
    )
    assert result.exit_code == 0
    assert "Untagged as foo: greetings" in result.output


def test_unencrypt_store(runner):
    with open(TEST_GPG_ID_FILE_PATH, "w") as f:
        f.write("abc@xyz.com")
    result = runner.invoke(cli, ["unencrypt-store", "--force"])
    assert result.exit_code == 0
    assert result.output.endswith("Store was unencrypted.\n")


def test_unencrypt_aborts_if_not_confirmed(runner):
    result = runner.invoke(cli, ["unencrypt-store"], input="\n")
    assert result.exit_code == 1
