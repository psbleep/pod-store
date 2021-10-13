import json

from abc import ABC, abstractmethod


class StoreFileHandler(ABC):
    def __init__(self, store_file_path: str):
        self._store_file_path = store_file_path

    @classmethod
    def create_with_file(cls, store_file_path: str):
        """Creates an empty store file while constructing the class."""
        file_handler = cls(store_file_path)
        file_handler.write_data({})
        return file_handler

    @abstractmethod
    def read_data(self):
        pass

    @abstractmethod
    def write_data(self, data: dict):
        pass


class UnencryptedStoreFileHandler(StoreFileHandler):
    """Class for reading/writing data from the store file.

    _store_file_path (str): file system location of the json file that holds store data.
    """

    def __init__(self, store_file_path):
        self._store_file_path = store_file_path

    def __repr__(self):
        return "<UnencryptedStoreFileHandler({self._store_file_path!r})>"

    def read_data(self):
        """Return json data from the store file."""
        with open(self._store_file_path) as f:
            return json.load(f)

    def write_data(self, data: dict):
        """Write json data to the store file."""
        with open(self._store_file_path, "w") as f:
            json.dump(data, f, indent=2)
