"""Encrypted CLI podcast tracker that syncs across devices. Inspired by `pass`."""
import os
from typing import Optional

# The version is set automatically within the Github action for building a new
# PyPI release: `pod_store./github/workflows/release.yml`
#
# A version number is read from the tag of the Github Release that triggers the PyPI
# release process, and that version written to the `pod-store/VERSION` file, where it
# can be read here and picked up by the `setup.cfg` file in the build process.
#
# Since the version is being determined dynamically at build time, the version file
# is not checked into version control and a default value is provided here for running
# the code outside the release build process (v0.0.0).
version_file = os.path.join(os.path.dirname(__file__), "VERSION")
if not os.path.exists(version_file):
    version = "v0.0.0"
else:
    with open(version_file) as f:
        version = f.read()
version = version.lstrip("v")

__author__ = "Patrick Schneeweis"
__docformat__ = "markdown en"
__license__ = "GPLv3+"
__title__ = "pod-store"
__version__ = version

DEFAULT_ENCRYPTED_STORE_FILE_NAME = "pod-store.gpg"
DEFAULT_UNENCRYPTED_STORE_FILE_NAME = "pod-store.json"
DEFAULT_PODCAST_DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Podcasts")
DEFAULT_TIMEOUT = 15
DEFAULT_STORE_PATH = os.path.join(os.path.expanduser("~"), ".pod-store")


def get_store_file_path(
    store_file_name: Optional[str] = None,
    gpg_id: Optional[str] = None,
) -> str:
    store_file_name = store_file_name or get_default_store_file_name(gpg_id)
    return os.path.join(STORE_PATH, store_file_name)


def get_default_store_file_name(gpg_id: Optional[str] = None) -> str:
    if gpg_id:
        return DEFAULT_ENCRYPTED_STORE_FILE_NAME
    else:
        return DEFAULT_UNENCRYPTED_STORE_FILE_NAME


STORE_PATH = os.path.abspath(os.getenv("POD_STORE_PATH", DEFAULT_STORE_PATH))

GPG_ID_FILE_PATH = os.getenv(
    "POD_STORE_GPG_ID_FILE", os.path.join(STORE_PATH, ".gpg-id")
)
try:
    with open(GPG_ID_FILE_PATH) as f:
        GPG_ID = f.read()
except FileNotFoundError:
    GPG_ID = None

STORE_FILE_NAME = os.getenv("POD_STORE_FILE_NAME", get_default_store_file_name(GPG_ID))
STORE_FILE_PATH = get_store_file_path(store_file_name=STORE_FILE_NAME, gpg_id=GPG_ID)
STORE_GIT_REPO = os.path.join(STORE_PATH, ".git")


DO_NOT_SET_EPISODE_METADATA = os.getenv("DO_NOT_SET_POD_STORE_EPISODE_METADATA", False)
EPISODE_DOWNLOAD_TIMEOUT = float(
    os.getenv("POD_STORE_EPISODE_DOWNLOAD_TIMEOUT", DEFAULT_TIMEOUT)
)

PODCAST_DOWNLOADS_PATH = os.path.abspath(
    os.getenv("POD_STORE_PODCAST_DOWNLOADS_PATH", DEFAULT_PODCAST_DOWNLOADS_PATH)
)
PODCAST_REFRESH_TIMEOUT = float(
    os.getenv("POD_STORE_PODCAST_REFRESH_TIMEOUT", DEFAULT_TIMEOUT)
)

SECURE_GIT_MODE = os.getenv("POD_STORE_SECURE_GIT_MODE", False)
EXTREME_SECURE_GIT_MODE = os.getenv("POD_STORE_EXTREME_SECURE_GIT_MODE", False)
