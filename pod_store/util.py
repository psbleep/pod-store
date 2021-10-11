import subprocess
from datetime import datetime
from typing import Optional

from . import STORE_PATH
from .exc import GitCommandError


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


def run_git_command(cmd):
    try:
        proc = subprocess.run(
            f"git {cmd}", cwd=STORE_PATH, capture_output=True, check=True, shell=True
        )
        return proc.stdout.decode()
    except subprocess.CalledProcessError as err:
        stderr = err.stderr.decode()
        raise GitCommandError(f"{cmd}: {stderr}")
