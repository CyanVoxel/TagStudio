# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""TagStudio launcher."""

from parse_args import parse_args
from src.cli.ts_cli import CliDriver  # type: ignore
from src.core.logging import get_logger, setup_logging
from src.core.ts_core import TagStudioCore
from src.qt.ts_qt import QtDriver


def main() -> None:
    # appid = "cyanvoxel.tagstudio.9"
    # ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

    setup_logging()
    logger = get_logger(__name__)

    # Parse arguments.
    args = parse_args()

    core = TagStudioCore()  # The TagStudio Core instance. UI agnostic.
    driver = None  # The UI driver instance.
    ui_name: str = "unknown"  # Display name for the UI, used in logs.

    # Driver selection based on parameters.
    match args.ui:
        case "qt":
            driver = QtDriver(core, args)
            ui_name = "Qt"
        case "cli":
            driver = CliDriver(core, args)
            ui_name = "CLI"
        case _:
            driver = QtDriver(core, args)
            ui_name = "Qt"

    try:
        driver.start()
    except Exception:
        logger.exception(
            f"\nTagStudio Frontend ({ui_name}) Crashed! Press Enter to Continue..."
        )

        input()


if __name__ == "__main__":
    main()
