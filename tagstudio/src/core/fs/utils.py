import os
import sys


def user_data_dir(app_name: str, version: str):
    r"""
    Get OS specific data directory path for the application data directory. Will be version specific.

    Parameters
    ----------
    app_name: str
        The name of the application
    version: str
        The version of the application

    Returns
    -------
    `str`
        The absolute path to the data directory

    Raises
    ------
    ValueError
        If the username is not found in the environment variables on Windows
    NotImplementedError
        If the OS is not supported

    Notes
    -----
    For Unix, we follow the XDG spec and support $XDG_DATA_HOME if defined.

    Data directories are:
        macOS:    `~/Library/Application Support/<app name>/<version>`
        Unix:     `$XDG_DATA_HOME/<app name>/<version>`
        Win 10:   `C:\Users\<username>\AppData\Local\<app name>\<version>`
    """
    app_name = app_name.lower()
    if (
        sys.platform.startswith("win")
        or sys.platform == "cygwin"
        or sys.platform == "msys"
    ):
        USN = os.getenv("USERNAME")
        if USN is None:
            raise ValueError(
                "Could not find the username in the environment variables."
            )
        os_path = f"C:\\Users\\{USN}\\AppData\\Local"
    elif sys.platform == "darwin":
        os_path = "~/Library/Application Support"
    elif sys.platform == "linux":
        os_path = os.getenv("XDG_DATA_HOME", os.path.expanduser("~"))
    else:
        raise NotImplementedError(f"Unsupported OS: {sys.platform}")

    return os.path.abspath(os.path.join(os_path, app_name, version))
