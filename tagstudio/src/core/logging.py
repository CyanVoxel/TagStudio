import logging
from contextvars import ContextVar

_root_logger = logging.getLogger()
_main_logger = _root_logger.getChild("tag_studio")

_main_logger_context_var: ContextVar[logging.Logger] = ContextVar("main_logger")
_main_logger_context_var.set(_main_logger)


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s: %(message)s", level=logging.DEBUG
    )


def get_logger(name: str) -> logging.Logger:
    main_logger = _main_logger_context_var.get()

    return main_logger.getChild(name)
