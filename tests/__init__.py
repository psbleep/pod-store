import os
from collections import namedtuple

TEST_STORE_PATH = os.path.join(os.path.dirname(__file__), "pypod-store")

TEST_GPG_ID_FILE_PATH = os.path.join(TEST_STORE_PATH, ".gpg-id")
TEST_STORE_FILE_PATH = os.path.join(TEST_STORE_PATH, "pod-store.json")
TEST_PODCAST_DOWNLOADS_PATH = os.path.join(os.path.dirname(__file__), "pypod-downloads")
TEST_PODCAST_EPISODE_DOWNLOADS_PATH = os.path.join(TEST_PODCAST_DOWNLOADS_PATH, "hello")

fake_process = namedtuple("FakeProc", ["stdout", "stderr"])
