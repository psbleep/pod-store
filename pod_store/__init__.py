"""Encrypted CLI podcast tracker that syncs across devices.

Inspired by `pass`.
"""

import os

__author__ = "Patrick Schneeweis"
__docformat__ = "markdown en"
__license__ = "GPLv3+"
__title__ = "pod-store"
__version__ = "0.0.1"

DEFAULT_STORE_PATH = os.path.join(os.path.expanduser("~"), ".pod-store")
DEFAULT_PODCAST_DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Podcasts")

STORE_PATH = os.path.abspath(os.getenv("POD_STORE_PATH", DEFAULT_STORE_PATH))

STORE_FILE_NAME = os.getenv("POD_STORE_FILE_NAME", "pod-store.json")
STORE_FILE_PATH = os.path.join(STORE_PATH, STORE_FILE_NAME)

GPG_ID_FILE_PATH = os.path.join(STORE_PATH, ".gpg-id")
try:
    with open(GPG_ID_FILE_PATH) as f:
        GPG_ID = f.read()
except FileNotFoundError:
    GPG_ID = None

PODCAST_DOWNLOADS_PATH = os.path.abspath(
    os.getenv("POD_STORE_PODCAST_DOWNLOADS_PATH", DEFAULT_PODCAST_DOWNLOADS_PATH)
)
