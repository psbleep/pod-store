import os

DEFAULT_STORE_PATH = os.path.join(os.path.expanduser("~"), ".pod-store")
DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser("~"), "Podcasts")

STORE_PATH = os.path.abspath(os.getenv("PYPOD_STORE_PATH", DEFAULT_STORE_PATH))
DOWNLOADS_PATH = os.path.abspath(
    os.getenv("PYPOD_DOWNLOADS_PATH", DEFAULT_DOWNLOAD_PATH)
)

STORE_EPISODE_FILE_EXTENSION = ".episode.json"
STORE_PODCAST_FILE_EXTENSION = ".podcast.json"
