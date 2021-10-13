import os

DEFAULT_STORE_PATH = os.path.join(os.path.expanduser("~"), ".pod-store")
DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser("~"), "Podcasts")

STORE_PATH = os.path.abspath(os.getenv("PYPOD_STORE_PATH", DEFAULT_STORE_PATH))
STORE_FILE_NAME = os.getenv("PYPOD_STORE_FILE_NAME", "pod-store.json")
STORE_FILE_PATH = os.path.join(STORE_PATH, STORE_FILE_NAME)
DOWNLOADS_PATH = os.path.abspath(
    os.getenv("PYPOD_DOWNLOADS_PATH", DEFAULT_DOWNLOAD_PATH)
)
