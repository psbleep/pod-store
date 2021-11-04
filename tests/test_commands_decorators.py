import json
from collections import namedtuple
from unittest.mock import call

import click
import pytest

from pod_store.commands.decorators import (
    catch_pod_store_errors,
    git_add_and_commit,
    require_store,
    save_store_changes,
)
from pod_store.exc import EpisodeDoesNotExistError, StoreDoesNotExistError

from . import TEST_STORE_FILE_PATH

fake_ctx = namedtuple("fake_ctx", ["obj", "params"])


def test_catch_pod_store_errors_decorator_aborts_command_and_displays_error_message(
    mocked_command_helpers_click_secho,
):
    @catch_pod_store_errors
    def raise_error():
        raise EpisodeDoesNotExistError("hello")

    with pytest.raises(click.Abort):
        raise_error()

    mocked_command_helpers_click_secho.assert_called_with(
        "Episode not found: hello.", fg="red"
    )


def test_git_add_and_commit_adds_changes_and_builds_commit_message(mocker):
    mocked_run_git_command = mocker.patch(
        "pod_store.commands.decorators.run_git_command"
    )

    @git_add_and_commit(message="hello world")
    def committed(ctx):
        pass

    ctx = fake_ctx(obj=None, params=None)
    committed(ctx)

    mocked_run_git_command.assert_has_calls(
        [call("add ."), call("commit -m 'hello world'")]
    )


def test_require_store_does_not_raise_error_if_store_exists(store):
    @require_store
    def store_exists(ctx):
        return ctx.obj

    ctx = fake_ctx(obj=store, params=None)

    assert store_exists(ctx) == store


def test_require_store_raises_error_if_store_does_not_exist():
    @require_store
    def no_store(ctx):
        return ctx.obj

    ctx = fake_ctx(obj=None, params=None)

    with pytest.raises(StoreDoesNotExistError):
        no_store(ctx)


def test_save_store_changes_saves_current_store_state_in_store_file(store):
    store.podcasts.delete("other")
    ctx = fake_ctx(obj=store, params=None)

    @save_store_changes
    def saved(ctx):
        pass

    saved(ctx)

    with open(TEST_STORE_FILE_PATH) as f:
        assert "other" not in json.load(f)
