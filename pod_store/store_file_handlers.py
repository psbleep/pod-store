import json
import os
import subprocess

from abc import ABC, abstractmethod

from .exc import GPGCommandError


class StoreFileHandler(ABC):
    def __init__(self, store_file_path: str):
        self._store_file_path = store_file_path

    @classmethod
    def create_with_file(cls, store_file_path: str, **kwargs):
        """Creates an empty store file while constructing the class."""
        file_handler = cls(store_file_path=store_file_path, **kwargs)
        file_handler.write_data({})
        return file_handler

    @abstractmethod
    def read_data(self):
        pass

    @abstractmethod
    def write_data(self, data: dict):
        pass


class EncryptedStoreFileHandler(StoreFileHandler):
    def __init__(self, gpg_id: str, *args, **kwargs):
        self._gpg_id = gpg_id
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<EncryptedStoreFileHandler({self._store_file_path!r})>"

    def read_data(self):
        cmd = f"gpg -d {self._store_file_path}"
        decrypted = self._run_gpg_command(cmd)
        return json.loads(decrypted)

    def write_data(self, data: dict):
        try:
            with open(self._store_file_path, "rb") as f:
                existing_data = f.read()
            os.remove(self._store_file_path)
        except FileNotFoundError:
            existing_data = b""

        tmp_file = os.path.join(os.path.dirname(self._store_file_path), ".tmp")
        with open(tmp_file, "w") as f:
            json.dump(data, f)

        try:
            cmd = (
                f"gpg --output {self._store_file_path} "
                "--encrypt "
                f"--recipient {self._gpg_id} "
                f"{tmp_file}"
            )
            self._run_gpg_command(cmd)
        except Exception as err:
            os.remove(tmp_file)
            with open(self._store_file_path, "wb") as f:
                f.write(existing_data)
            raise GPGCommandError(str(err))

        os.remove(tmp_file)

    @staticmethod
    def _run_gpg_command(cmd: str):
        proc = subprocess.run(cmd, capture_output=True, check=True, shell=True)
        return proc.stdout.decode()


class UnencryptedStoreFileHandler(StoreFileHandler):
    """Class for reading/writing data from an unencrypted store file.

    _store_file_path (str): file system location of the json file that holds store data.
    """

    def __repr__(self):
        return f"<UnencryptedStoreFileHandler({self._store_file_path!r})>"

    def read_data(self):
        """Retrieve unencrypted json data from the store file."""
        with open(self._store_file_path) as f:
            return json.load(f)

    def write_data(self, data: dict):
        """Write encrypted json data to the store file."""
        with open(self._store_file_path, "w") as f:
            json.dump(data, f, indent=2)
