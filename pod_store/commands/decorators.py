"""Decorators used on the Click commands defined in `pod_store.__main__`."""

import functools
import os
from typing import Any, Callable, List

import click

from .. import STORE_GIT_REPO
from ..exc import ShellCommandError
from ..util import run_git_command
from .helpers import display_pod_store_error_from_exception


def catch_pod_store_errors(f: Callable) -> Callable:
    """Decorator for catching pod store errors and rendering a more-friendly error
    message to the user.
    """

    @functools.wraps(f)
    def catch_pod_store_errors_inner(*args, **kwargs) -> Any:
        try:
            return f(*args, **kwargs)
        except Exception as err:
            display_pod_store_error_from_exception(err)

    return catch_pod_store_errors_inner


def default_commit_message_builder(
    ctx_params: dict, message: str, params: List[str] = None
) -> str:
    """Helper to build `git` commit messages from the Click command context.

    `message` should be the intended `git` commit message.

    If `message` is a template string, `params` acts as a list of Click context
    param names that will be passed to the `message` template string as
    keyword arguments.

    Example:

        default_commit_message_builder(
            ctx_params={"thing": "world"},
            message="Hello {thing}.",
            params=["thing"]
        )

    Output:

        Hello world.

    See the `git_add_and_commit` decorator for more information.
    """
    params = params or []
    message_kwargs = {p: ctx_params[p] for p in params}
    return message.format(**message_kwargs)


def git_add_and_commit(
    commit_message_builder: Callable = default_commit_message_builder,
    **commit_message_builder_kwargs,
) -> Callable:
    """Decorator for checking in and commiting git changes made after running a command.

    If no git repo is detected within the pod store, this will be a no-op.

    Requires the `click.Context` object as a first argument to the decorated function.
    (see `click.pass_context`)

    For default behavior, check out the `default_commit_message_builder` helper
    function docs.

    For custom behavior, pass in a callable as a keyword arugment for
    `commit_message_builder`.

    The message builder callable will receive a `ctx_params` dict
    (passed in from `click.Context.params`), and any additional keyword
    arguments for the decorator will be passed on as well.
    """

    def git_add_and_commit_wrapper(f: Callable) -> Callable:
        @functools.wraps(f)
        def git_add_and_commit_inner(ctx: click.Context, *args, **kwargs) -> Any:
            resp = f(ctx, *args, **kwargs)
            if not os.path.exists(STORE_GIT_REPO):
                return resp

            run_git_command("add .")
            commit_msg = commit_message_builder(
                ctx_params=ctx.params, **commit_message_builder_kwargs
            )
            try:
                run_git_command(f"commit -m {commit_msg!r}")
            except ShellCommandError:
                pass
            return resp

        return git_add_and_commit_inner

    return git_add_and_commit_wrapper


def save_store_changes(f: Callable) -> Callable:
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
