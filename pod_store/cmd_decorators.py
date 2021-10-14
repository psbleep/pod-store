import functools
from typing import Any, Callable

import click

from .exc import (
    EpisodeDoesNotExistError,
    GPGCommandError,
    NoEpisodesFoundError,
    NoPodcastsFoundError,
    PodcastDoesNotExistError,
    PodcastExistsError,
    ShellCommandError,
    StoreExistsError,
)
from .util import run_git_command


def catch_pod_store_errors(f: Callable):
    """Decorator for catching pod store errors and rendering a more-friendly error
    message to the user.
    """

    @functools.wraps(f)
    def catch_pod_store_errors_inner(*args, **kwargs) -> Any:
        try:
            return f(*args, **kwargs)
        except EpisodeDoesNotExistError as err:
            msg = str(err)
            click.secho(f"Episode not found: {msg}", fg="red")
        except GPGCommandError as err:
            msg = str(err)
            click.secho("Error running GPG command: {msg}", fg="red")
        except NoEpisodesFoundError:
            click.secho("No episodes found.", fg="red")
        except NoPodcastsFoundError:
            click.secho("No podcasts found.", fg="red")
        except PodcastDoesNotExistError as err:
            msg = str(err)
            if msg == "None":
                msg = "not specified"
            click.secho(f"Podcast not found: {msg}", fg="red")
        except PodcastExistsError as err:
            msg = str(err)
            click.secho(f"Podcast with title already exists: {msg}", fg="red")
        except ShellCommandError as err:
            msg = str(err)
            click.secho(f"Error running shell command: {msg}", fg="red")
        except StoreExistsError as err:
            msg = str(err)
            click.secho(f"Store already initialized: {msg}", fg="red")

    return catch_pod_store_errors_inner


def _default_commit_message_builder(
    ctx_params: dict, commit_message_template: str, *param_names
) -> str:
    """Helper to build `git` commit messages from the Click command context.

    See the `git_add_and_commit` decorator for more information.
    """
    template_args = [ctx_params[p] for p in param_names]
    return commit_message_template.format(*template_args)


def git_add_and_commit(
    *builder_args,
    commit_message_builder: Callable = _default_commit_message_builder,
):
    """Decorator for checking in and commiting changes made after running a command.
    Requires the `click.Context` object as a first argument to the decorated function.
    (see `click.pass_context`)

    By default, pass in a template str for building the commit message and a list of
    param names to grab from the `click.Context.params` dict to populate it.

        @click.pass_context
        @git_add_and_commit("Hello {}.", "recepient")
        def cmd(ctx):
            ...

    Assuming the `click.Context.params` dict had a key `recepient` with the value
    "world", the resulting commit message would be:

        "Hello world."

    Pass in a callable as a keyword arugment for `commit_message_builder` to get custom
    behavior when building commit messages.

    The message builder callable will receive a `ctx_params` dict
    (passed in from `click.Context.params`), and any positional `builder_args`
    provided to the decorator. It should return the commit message as a string.


        def custom_message_builder(_, value):
            return "This commit message is {}.".format(value)

        @click.pass_context
        @git_add_and_commit("arbitrary", commit_message_builder=custom_message_builder)
        def cmd(ctx):
            ...

    Here the resulting commit message would be:

        "This commit message is arbitrary."
    """

    def git_add_and_commit_wrapper(f: Callable):
        @functools.wraps(f)
        def git_add_and_commit_inner(ctx: click.Context, *args, **kwargs) -> Any:
            resp = f(ctx, *args, **kwargs)
            run_git_command("add .")
            commit_msg = commit_message_builder(ctx.params, *builder_args)
            try:
                run_git_command(f"commit -m {commit_msg!r}")
            except ShellCommandError:
                pass
            return resp

        return git_add_and_commit_inner

    return git_add_and_commit_wrapper


def optional_podcast_commit_message_builder(
    ctx_params: dict, commit_message_template: str
) -> str:
    """Helper to build `git` commit messages for Click commands that
    have an optional `podcast` argument.

    See the `git_add_and_commit` decorator for more information.
    """
    podcast_name = ctx_params.get("podcast") or "all"
    return commit_message_template.format(podcast_name)


def save_store_changes(f: Callable):
    """Decorator for saving changes to the store after running a command.

    Requires a `click.Context` object as the first positional argument to the wrapped
    function, with the `obj` attribute set to the active `pod_store.store.Store` object.

    See `click.pass_context` for more about the `Context` object.
    """

    @functools.wraps(f)
    def save_store_changes_inner(ctx: click.Context, *args, **kwargs) -> Any:
        resp = f(ctx, *args, **kwargs)
        ctx.obj.save()
        return resp

    return save_store_changes_inner
