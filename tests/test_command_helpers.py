from unittest.mock import Mock

import click
import pytest

from pod_store.commands.helpers import (
    abort_if_false,
    display_pod_store_error_from_exception,
)
from pod_store.exc import (
    AmbiguousEpisodeError,
    EpisodeDoesNotExistError,
    GPGCommandError,
    NoEpisodesFoundError,
    NoPodcastsFoundError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    ShellCommandError,
    StoreDoesNotExistError,
    StoreExistsError,
    StoreIsNotEncrypted,
    StoreLocked,
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
    (
        AmbiguousEpisodeError(23),
        "Cannot determine intended episode: 23. "
        "Please indicate which podcast this episode belongs to.",
    ),
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
    (
        StoreDoesNotExistError(),
        "Store has not been set up. See the `init` command for set up instructions.",
    ),
    (StoreExistsError("/path"), "Store already initialized: /path."),
    (
        StoreIsNotEncrypted("/path/to/gpg-id"),
        "Store has not been set up with a GPG encryption key. "
        "Please verify whether the store is encrypted. "
        "If it is, place a text file containing the GPG key used to encrypt it at: "
        "/path/to/gpg-id",
    ),
    (StoreLocked(), "Store locked by another command."),
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
