"""Utility functions used in more than one place."""

import subprocess
from datetime import datetime
from typing import Any, Optional, TypeVar, Union

from . import STORE_PATH
from .episodes import Episode
from .exc import ShellCommandError

P = TypeVar("Podcast")


def meets_list_filter_criteria(obj: Union[Episode, P], key: str, value: Any) -> bool:
    """Used to filter a list of podcasts or episodes in
    `pod_store.podcasts.PodcastEpisodes.list` or `pod_store.store.StorePodcasts.list`.

    Checks if the attribute `key` on the object `obj` matches the supplied `value`.

    If no attribute is found on `obj` to match `key`, attempts to check for tags.

       - if `value` is True: check for presence of a tag named `key`
       - if `value` is False: check for absence of a tag named `key`
    """
    try:
        return getattr(obj, key) == value
    except AttributeError as err:
        if value is True:
            return key in obj.tags
        elif value is False:
            return key not in obj.tags
        else:
            raise err


def parse_datetime_from_json(dt: datetime) -> Optional[datetime]:
    """Parses a Python `datetime` object from an isoformat string.

    Tolerates empty values and returns `None`
    """
    if dt:
        return datetime.fromisoformat(dt)
    else:
        return None


def parse_datetime_to_json(dt: datetime) -> Optional[str]:
    """Converts a Python `datetime` object into an isoformat string.

    Tolerates empty values and returns `None`
    """
    if dt:
        return dt.isoformat()
    else:
        return None


def run_git_command(cmd: str) -> str:
    """Run a `git` command.

    Will run the resulting command with the cwd set to the git repo location.

    Returns stdout from the shell command if successful.
    """
    return run_shell_command(f"git {cmd}", cwd=STORE_PATH)


def run_shell_command(cmd, cwd: Optional[str] = None) -> str:
    """Run a shell command.

    If the command fails, a `pod_store.exc.ShellCommandError` is raised, with
    the contents of stderr provided as the error message.

    Returns stdout from the shell command if successful.
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=True, shell=True)
        return proc.stdout.decode()
    except subprocess.CalledProcessError as err:
        stderr = err.stderr.decode()
        raise ShellCommandError(f"{cmd}: {stderr}")
