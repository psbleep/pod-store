"""Decorators used on the Click commands defined in `pod_store.__main__`."""

import functools
import hashlib
import os
import time
from typing import Any, Callable, Optional

import click

from .. import EXTREME_SECURE_GIT_MODE, SECURE_GIT_MODE, STORE_GIT_REPO
from ..exc import ShellCommandError, StoreDoesNotExistError
from ..util import run_git_command
from .commit_messages import default_commit_message_builder
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


def conditional_confirmation_prompt(
    override: Optional[str] = None, **conditions
) -> Callable:
    """Decorator for prompting the user to confirm the command if conditions are met.

    Conditions are passed as a set of key/value pairs that represent Click command
    params and values. If the params match the expected values, the user will be
    prompted to confirm that they want to run this command.

    The `override` argument can be set to the name of a flag param that will skip this
    confirmation.

    For example:

    @conditional_confirmation_prompt(hello="world", foo="bar", override="force")
    ...

    Would show a prompt if both of these conditions were met:

        - `hello` param had a value of 'world', `foo` param had a value of 'bar'
        - the `force` parameter was not set to True

    If the user does not confirm the action, the command is aborted.
    """

    def conditional_confirmation_prompt_wrapper(f: Callable) -> Callable:
        @functools.wraps(f)
        def conditional_confirmation_prompt_inner(ctx, *args, **kwargs) -> Any:
            if ctx.params.get(override) is not True:
                for param, value in conditions.items():
                    if ctx.params.get(param) != value:
                        break
                else:
                    if click.prompt("Confirm?", type=click.Choice(["y", "n"])) != "y":
                        raise click.Abort()
            return f(ctx, *args, **kwargs)

        return conditional_confirmation_prompt_inner

    return conditional_confirmation_prompt_wrapper


def git_add_and_commit(
    secure_git_mode_message: str = "",
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

            if EXTREME_SECURE_GIT_MODE:
                commit_msg = hashlib.sha256(str(time.time()).encode()).hexdigest()
            elif SECURE_GIT_MODE:
                commit_msg = secure_git_mode_message
            else:
                commit_msg = commit_message_builder(
                    ctx_params=ctx.params, **commit_message_builder_kwargs
                )

            run_git_command("add .")
            try:
                run_git_command(f"commit -m {commit_msg!r}")
            except ShellCommandError:
                pass
            return resp

        return git_add_and_commit_inner

    return git_add_and_commit_wrapper


def require_store(f: Callable) -> Callable:
    """Decorator for commands that require the pod store to be initialized.

    Will raise an exception if the Click context is passed without a value assigned
    for `ctx.obj`.

    If a value has been assigned to `ctx.obj`, assume it is the pod store and carry on.
    """

    @functools.wraps(f)
    def require_store_inner(ctx: click.Context, *args, **kwargs):
        if not ctx.obj:
            raise StoreDoesNotExistError()
        return f(ctx, *args, **kwargs)

    return require_store_inner


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
