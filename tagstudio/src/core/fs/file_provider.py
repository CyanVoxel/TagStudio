import ctypes
import logging
import multiprocessing
import os
import sys
from datetime import datetime
from typing import Callable, List, TypedDict, Union

from PySide6.QtCore import QFileSystemWatcher, QObject, QThread, Signal, Slot

logger = logging.getLogger(__name__)


class Metadata(TypedDict):
    """A dictionary containing the metadata of a file.

    Attributes
    ----------
    file_path: `str`
        The path to the file as a normalized string using system separators (e.g. / or \)
    unique_id: `str`
        A unique identifier for the file. THIS IS NOT GUARANTEED TO BE UNIQUE ACROSS SYSTEMS OR VOLUMES. It of variable length and format depending on the system.
    size: `int`
        The size of the file in bytes
    creation_time: `float`
        The creation time of the file as a Unix timestamp
    last_access_time: `float`
        The last access time of the file as a Unix timestamp
    last_write_time: `float`
        The last write time of the file as a Unix timestamp

    """

    file_path: str
    unique_id: str
    size: int
    creation_time: float
    last_access_time: float
    last_write_time: float


class MetadataError(TypedDict):
    error: str
    path: str


MetadataCallback = Callable[[List[Metadata], List[MetadataError]], None]


def _filetime_to_dt(ft: ctypes.wintypes.FILETIME) -> float:
    """Convert Windows FILETIME to datetime"""
    us = (ft.dwHighDateTime << 32) + ft.dwLowDateTime
    us = (
        us // 10 - 11644473600000000
    )  # Convert from 100ns intervals to microseconds since Unix epoch
    return datetime.timestamp(us / 1e6)


def _get_windows_metadata(file_path: str) -> Union[Metadata, MetadataError]:
    """Retrieve and normalizes metadata specific to Windows.

    Parameters
    ----------
    file_path: str
        The path to the file

    Returns
    -------
    `Metadata`
        A dictionary containing the metadata of the file

    Raises
    ------
    Exception
        If an error occurs while processing the file

    """
    try:
        file_handle = ctypes.windll.kernel32.CreateFileW(
            file_path, 0x00, 0x01 | 0x02 | 0x04, None, 0x03, 0x02000000, None
        )
        if file_handle == -1:
            raise ctypes.WinError()

        info = ctypes.wintypes.BY_HANDLE_FILE_INFORMATION()
        if not ctypes.indll.kernel32.GetFileInformationByHandle(
            file_handle, ctypes.byref(info)
        ):
            raise ctypes.WinError()

        ctypes.windll.kernel32.CloseHandle(file_handle)
        return Metadata(
            file_path=file_path,
            unique_id=f"{info.dwVolumeSerialNumber}-{info.nFileIndexHigh}-{info.nFileIndexLow}",
            size=(info.nFileSizeHigh << 32) + info.nFileSizeLow,
            creation_time=_filetime_to_dt(info.ftCreationTime),
            last_access_time=_filetime_to_dt(info.ftLastAccessTime),
            last_write_time=_filetime_to_dt(info.ftLastWriteTime),
        )

    except Exception as e:
        return {"error": str(e), "path": file_path}


def _get_unix_metadata(file_path: str) -> Union[Metadata, MetadataError]:
    """Retrieve and normalize metadata specific to UNIX-like systems.

    Parameters
    ----------
    file_path: str
        The path to the file

    Returns
    -------
    `Metadata`
        A dictionary containing the metadata of the file

    Raises
    ------
    Exception
        If an error occurs while processing the file

    """
    try:
        stats = os.stat(file_path)
        return Metadata(
            file_path=file_path,
            unique_id=f"{stats.st_dev}-{stats.st_ino}",
            size=stats.st_size,
            creation_time=stats.st_ctime,
            last_access_time=stats.st_atime,
            last_write_time=stats.st_mtime,
        )
    except Exception as e:
        return {"error": str(e), "path": file_path}


class FileScanner(QObject):
    scanning_complete = Signal(list)

    def __init__(
        self, root_directories: List[str], num_workers: Union[int, None] = None
    ):
        self.root_directories = root_directories

        if num_workers is None:
            self.num_workers = multiprocessing.cpu_count()
            if self.num_workers - 1 > 0:
                self.num_workers -= 1
        else:
            self.num_workers = num_workers

        self.directory_queue = multiprocessing.Queue()
        self.results: List[Metadata] = multiprocessing.Manager().list()
        self.errors: List[MetadataError] = multiprocessing.Manager().list()
        self.kill_switch = multiprocessing.Event()
        self.workers = []

    def init_workers(self):
        # To minmize branching in the thread, we have system based workers
        # It's a bit more duplication but it's slightly faster as the 3.11 interpreter did not branch predict this
        if sys.platform == "win32" or sys.platform == "cygwin":
            self.workers = [
                multiprocessing.Process(target=self.win_worker)
                for _ in range(self.num_workers)
            ]
        elif sys.platform == "linux" or sys.platform == "darwin":
            self.workers = [
                multiprocessing.Process(target=self.unix_worker)
                for _ in range(self.num_workers)
            ]
        else:
            raise NotImplementedError(f"Unsupported OS: {self.os_name}")

    def start_workers(self):
        for worker in self.workers:
            worker.start()
        for worker in self.workers:
            worker.join()

    def stop_workers(self):
        self.kill_switch.set()

    def win_worker(self):
        while not self.directory_queue.empty():
            if self.kill_switch.is_set():
                break
            directory = self.directory_queue.get()
            self.win_process_directory(directory)

    def unix_worker(self):
        while not self.directory_queue.empty():
            if self.kill_switch.is_set():
                break
            directory = self.directory_queue.get()
            self.unix_process_directory(directory)

    def win_process_directory(self, directory):
        try:
            for entry in os.scandir(directory):
                if entry.is_file():
                    # Apply file filters here if necessary
                    metadata = _get_windows_metadata(entry.path)
                    if "error" in metadata:
                        self.errors.append(metadata)
                    else:
                        self.results.append(metadata)
                elif entry.is_dir():
                    # Optionally filter directories here
                    self.directory_queue.put(entry.path)
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")

    def unix_process_directory(self, directory):
        try:
            for entry in os.scandir(directory):
                if entry.is_file():
                    # Apply file filters here if necessary
                    metadata = _get_unix_metadata(entry.path)
                    self.results.append(metadata)
                elif entry.is_dir():
                    # Optionally filter directories here
                    self.directory_queue.put(entry.path)
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")

    def run(self):
        """Start the metadata scanning process."""
        self.errors = []
        self.results = []
        for directory in self.root_directories:
            self.directory_queue.put(directory)
        self.start_workers()
        self.scanning_complete.emit(self.results)


class FileSystemProvider(QObject):
    """A class provides metadata scanning and file watching capabilities.

    You may use Signal and Slot decorators to connect to the signals emitted by this class. Or use the provide callbacks to accepted methods directly.

    """

    scanning_complete = Signal(list)

    def __init__(self, parent=None):
        super(FileSystemProvider, self).__init__(parent)
        self.init_watcher()

    def init_watcher(self):
        """Initialize the file system watcher."""
        self.watcher = QFileSystemWatcher()
        self.watcher_thread = QThread()
        self.watcher.moveToThread(self.watcher_thread)
        self.watcher_thread.start()

    @Slot(str)
    def watch_path(self, path: str):
        """Add a path to the file system watcher.

        Parameters
        ----------
        path: str
            The path to the file or directory to watch

        """
        self.watcher.addPath(path)

    @Slot(str)
    def unwatch_path(self, path: str):
        """Remove a path from the file system watcher.

        Parameters
        ----------
        path: str
            The path to the file or directory to unwatch

        """
        self.watcher.removePath(path)

    @Slot(list)
    def scan_files(
        self,
        root_directories: List[str],
        callback: MetadataCallback = None,
        num_workers: Union[int, None] = None,
    ):
        """Scan the files in the specified directories. You may provide a callback function to receive the metadata and errors after scanning is complete or you may connect to the scanning_complete.

        You may access the the metadata and results as they are being populated by scanning the `metadata.results` and `metadata.errors` properties.

        Parameters
        ----------
        root_directories: List[str]
            A list of top level directories to scan
        callback: Callable[[List[Metadata], List[MetadataError]], None],
            Optional, A callback function to receive the metadata and errors after scanning is complete.
        num_workers: Union[int, None]
            Optional, The number of workers to use for scanning. If None, the number of workers will be equal to the number of CPUs on the system.

        """
        self.metadata = FileScanner(root_directories, num_workers)
        self.metadata.scanning_complete.connect(self.scanning_complete)
        if callback:
            self.metadata.scanning_complete.connect(callback)
        self.metadata.run()

    @Slot()
    def stop_scan(self):
        """Stop the file scanning process."""
        self.metadata.stop_workers()

    def get_file_data(self, file_path: str) -> Union[Metadata, MetadataError]:
        """Retrieve the metadata for a file in a platform independent manner.

        Parameters
        ----------
        file_path: str
            The path to the file

        Returns
        -------
        `Metadata`
            A dictionary containing the metadata of the file

        """
        if sys.platform == "win32" or sys.platform == "cygwin":
            return _get_windows_metadata(file_path)
        elif sys.platform == "linux" or sys.platform == "darwin":
            return _get_unix_metadata(file_path)
        else:
            raise NotImplementedError(f"Unsupported OS: {sys.platform}")

    async def get_dir_files_metadata(
        self, directory: str
    ) -> List[Union[Metadata, MetadataError]]:
        """Retrieve the metadata for all the files in a directory. Note that this method is asynchronous and NOT recursive. **IT WILL BLOCK THE MAIN THREAD**

        If you want to scan many directories, use the `scan_files` method.

        Parameters
        ----------
        directory: str
            The path to the directory

        Returns
        -------
        List[Union[Metadata, MetadataError]]
            A list of dictionaries containing the metadata of the files

        """
        try:
            return [
                self.get_file_data(entry.path)
                for entry in os.scandir(directory)
                if entry.is_file()
            ]
        except Exception as e:
            return [{"error": str(e), "path": directory}]
