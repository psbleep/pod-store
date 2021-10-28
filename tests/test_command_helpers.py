from unittest.mock import Mock

import click
import pytest

from pod_store.commands.helpers import (
    abort_if_false,
    display_pod_store_error_from_exception,
)
from pod_store.exc import (
    EpisodeDoesNotExistError,
    GPGCommandError,
    NoEpisodesFoundError,
    NoPodcastsFoundError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    ShellCommandError,
    StoreExistsError,
)


@pytest.fixture
def mocked_ctx():
    return Mock()


def test_abort_if_false_will_abort(mocked_ctx):
    abort_if_false(mocked_ctx, None, value=False)
    mocked_ctx.abort.assert_called()


def test_abort_if_false_will_not_abort(mocked_ctx):
    abort_if_false(mocked_ctx, None, value=True)
    mocked_ctx.abort.assert_not_called()


exceptions_and_error_messages = [
    (EpisodeDoesNotExistError("hello"), "Episode not found: hello."),
    (
        GPGCommandError("foobar"),
        "Error encountered when running GPG commands: foobar.",
    ),
    (NoEpisodesFoundError(), "No episodes found. "),
    (NoPodcastsFoundError(), "No podcasts found. "),
    (PodcastDoesNotExistError("zaza"), "Podcast not found: zaza."),
    (PodcastExistsError("zozo"), "Podcast with title already exists: zozo."),
    (ShellCommandError("xyz"), "Error running shell command: xyz."),
    (StoreExistsError("/path"), "Store already initialized: /path."),
]


@pytest.mark.parametrize("exception,error_message", exceptions_and_error_messages)
def test_display_pod_store_error(
    exception,
    error_message,
    mocked_command_helpers_click_secho,
):
    with pytest.raises(click.Abort):
        display_pod_store_error_from_exception(exception)

    mocked_command_helpers_click_secho.assert_called_with(error_message, fg="red")
