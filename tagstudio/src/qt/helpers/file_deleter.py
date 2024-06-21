import logging
import traceback
from pathlib import Path
from collections.abc import Callable

ERROR = f"[ERROR]"
WARNING = f"[WARNING]"
INFO = f"[INFO]"

logging.basicConfig(format="%(message)s", level=logging.INFO)


def delete_file(path: str | Path, callback: Callable):
    _path = str(path)
    _file = Path(_path)
    logging.info(f"Deleting file: {_path}")
    if not _file.exists():
        logging.error(f"File not found: {_path}")
        return
    try:
        _file.unlink()
        callback()
    except Exception as exception:
        logging.exception(exception)


class FileDeleterHelper:
    def __init__(self, filepath: str | Path):
        self.filepath = filepath

    def set_filepath(self, filepath: str | Path):
        self.filepath = filepath

    def set_delete_callback(self, callback: Callable):
        self.delete_callback = callback

    def delete_file(self):
        delete_file(self.filepath, self.delete_callback)
