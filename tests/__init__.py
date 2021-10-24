import os
from collections import namedtuple

TEST_AUDIO_FILE_PATH = os.path.join(os.path.dirname(__file__), "sample.mp3")
TEST_STORE_PATH = os.path.join(os.path.dirname(__file__), "pod-store")

TEST_GPG_ID_FILE_PATH = os.path.join(TEST_STORE_PATH, ".gpg-id")
TEST_STORE_FILE_PATH = os.path.join(TEST_STORE_PATH, "pod-store.json")
TEST_PODCAST_DOWNLOADS_PATH = os.path.join(
    os.path.dirname(__file__), "pod-store-downloads"
)
TEST_PODCAST_EPISODE_DOWNLOADS_PATH = os.path.join(
    TEST_PODCAST_DOWNLOADS_PATH, "greetings"
)

fake_process = namedtuple("FakeProc", ["stdout", "stderr"])
