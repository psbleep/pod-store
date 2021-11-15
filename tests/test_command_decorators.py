import json
from collections import namedtuple
from unittest.mock import call

import click
import pytest

from pod_store.commands import decorators
from pod_store.exc import EpisodeDoesNotExistError, StoreDoesNotExistError

from . import TEST_STORE_FILE_PATH

fake_ctx = namedtuple("fake_ctx", ["obj", "params"])


@pytest.fixture
def mocked_run_git_command(mocker):
    return mocker.patch("pod_store.commands.decorators.run_git_command")


def test_catch_pod_store_errors_decorator_aborts_command_and_displays_error_message(
    mocked_command_helpers_click_secho,
):
    @decorators.catch_pod_store_errors
    def raise_error():
        raise EpisodeDoesNotExistError("hello")

    with pytest.raises(click.Abort):
        raise_error()

    mocked_command_helpers_click_secho.assert_called_with(
        "Episode not found: hello.", fg="red"
    )


def test_conditional_confirmation_prompt_params_do_not_match_all_conditions():
    @decorators.conditional_confirmation_prompt(hello=True, foo="bar")
    def no_match(ctx):
        return True

    ctx = fake_ctx(obj=None, params={"hello": True})
    assert no_match(ctx) is True


def test_conditional_confirmation_prompt_params_match_conditions_but_override_is_set():
    @decorators.conditional_confirmation_prompt(hello=True, override="flagged")
    def flagged(ctx):
        return True

    ctx = fake_ctx(obj=None, params={"hello": True, "flagged": True})
    assert flagged(ctx) is True


def test_conditional_confirmation_prompt_user_confirms_choice(
    mocker,
):
    mocker.patch("click.prompt", return_value="y")

    @decorators.conditional_confirmation_prompt(hello=True)
    def prompt_passed(ctx):
        return True

    ctx = fake_ctx(obj=None, params={"hello": True})
    assert prompt_passed(ctx) is True


def test_conditional_confirmation_prompt_user_does_not_confirm_choice(
    mocker,
):
    mocker.patch("click.prompt", return_value="n")

    @decorators.conditional_confirmation_prompt(hello=True)
    def prompt_failed(ctx):
        return True

    ctx = fake_ctx(obj=None, params={"hello": True})
    with pytest.raises(click.Abort):
        prompt_failed(ctx)


def test_git_add_and_commit_adds_changes_and_builds_commit_message(
    mocked_run_git_command,
):
    @decorators.git_add_and_commit(message="hello world")
    def committed(ctx):
        return True

    ctx = fake_ctx(obj=None, params=None)
    assert committed(ctx) is True

    mocked_run_git_command.assert_has_calls(
        [call("add ."), call("commit -m 'hello world'")]
    )


def test_git_add_and_commit_chooses_secure_message_if_secure_git_mode_is_configured(
    mocker,
    mocked_run_git_command,
):
    mocker.patch.object(decorators, "SECURE_GIT_MODE", True)

    @decorators.git_add_and_commit(
        message="hello world", secure_git_mode_message="<redacted> world"
    )
    def secure(ctx):
        return True

    assert secure(ctx=None) is True

    mocked_run_git_command.assert_has_calls(
        [call("add ."), call("commit -m '<redacted> world'")]
    )


def test_git_add_and_commit_chooses_random_message_if_extreme_git_mode_is_configured(
    mocker,
    mocked_run_git_command,
):
    fake_hash_obj = mocker.Mock()
    fake_hash_obj.hexdigest = mocker.Mock(return_value="abc123def")

    mocker.patch.object(decorators, "EXTREME_SECURE_GIT_MODE", True)
    mocker.patch(
        "pod_store.commands.decorators.hashlib.sha256", return_value=fake_hash_obj
    )

    @decorators.git_add_and_commit(
        message="hello world", secure_git_mode_message="<redacted> world"
    )
    def secure(ctx):
        return True

    assert secure(ctx=None) is True

    mocked_run_git_command.assert_has_calls(
        [call("add ."), call("commit -m 'abc123def'")]
    )


def test_git_add_and_commit_does_nothing_if_git_not_set_up(
    start_with_no_store, mocked_run_git_command
):
    @decorators.git_add_and_commit(message="hello world")
    def no_git(ctx):
        return True

    assert no_git(ctx=None) is True
    mocked_run_git_command.assert_not_called()


def test_require_store_does_not_raise_error_if_store_exists(store):
    @decorators.require_store
    def store_exists(ctx):
        return ctx.obj

    ctx = fake_ctx(obj=store, params=None)

    assert store_exists(ctx) == store


def test_require_store_raises_error_if_store_does_not_exist():
    @decorators.require_store
    def no_store(ctx):
        return ctx.obj

    ctx = fake_ctx(obj=None, params=None)

    with pytest.raises(StoreDoesNotExistError):
        no_store(ctx)


def test_save_store_changes_saves_current_store_state_in_store_file(store):
    store.podcasts.delete("other")
    ctx = fake_ctx(obj=store, params=None)

    @decorators.save_store_changes
    def saved(ctx):
        pass

    saved(ctx)

    with open(TEST_STORE_FILE_PATH) as f:
        assert "other" not in json.load(f)
