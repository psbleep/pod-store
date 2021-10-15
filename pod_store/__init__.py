"""Encrypted CLI podcast tracker that syncs across devices.

Inspired by `pass`.
"""
import os

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
