"""The bmaya logger. Plain Python: where the text goes is a slot, filled at startup.

Records go through one LogOutput handler, which writes each record with the writer registered for its level.
With nothing registered (plain Python, mayapy, batch jobs) every record goes to stdout, read at write time, so a
batch framework's stream capture sees it. bmaya.maya.startup.register() fills the slot with Maya's MGlobal display
functions in a GUI session (RigModules design/mayadev-ui.md, D49).
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Mapping
from typing import ClassVar

_LOGGER = None

LOG_FORMAT = "[%(levelname)s] %(filename)s:%(lineno)d >> %(message)s"


def _write_stdout(text: str) -> None:
    sys.stdout.write(text + "\n")


class LogOutput(logging.Handler):
    """Writes a record with the writer of the highest registered level at or below the record's level. A record
    below every registered level, or with none registered, goes to stdout."""

    writers: ClassVar[dict[int, Callable[[str], None]]] = {}

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.writer_for(record.levelno)(self.format(record))
        except Exception:
            self.handleError(record)

    @classmethod
    def writer_for(cls, level: int) -> Callable[[str], None]:
        levels = [registered for registered in cls.writers if registered <= level]
        return cls.writers[max(levels)] if levels else _write_stdout


def register_writers(writers: Mapping[int, Callable[[str], None]]) -> None:
    """Fills the log output slot: a writer per level (logging.INFO, logging.WARNING, ...). Replaces the writers
    registered before. Called only from a layer's startup.register()."""
    LogOutput.writers = dict(writers)


def reset_writers() -> None:
    """Puts the default back: everything to stdout."""
    LogOutput.writers = {}


def init_logger() -> logging.Logger:
    """Configures the bmaya logger with one LogOutput handler at INFO. Safe to call again."""
    global _LOGGER

    _LOGGER = logging.getLogger("bmaya")
    _LOGGER.setLevel(logging.DEBUG)
    for handler in _LOGGER.handlers[:]:
        _LOGGER.removeHandler(handler)

    handler = LogOutput()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
    handler.setLevel(logging.INFO)
    _LOGGER.addHandler(handler)
    _LOGGER.propagate = False
    return _LOGGER


def get_logger() -> logging.Logger:
    if _LOGGER is None:
        return init_logger()
    return _LOGGER


def debug(msg, *args, **kwargs) -> None:
    kwargs.setdefault("stacklevel", 2)
    get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs) -> None:
    kwargs.setdefault("stacklevel", 2)
    get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs) -> None:
    kwargs.setdefault("stacklevel", 2)
    get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs) -> None:
    if "exc_info" not in kwargs and sys.exc_info()[0] is not None:
        kwargs["exc_info"] = True
    kwargs.setdefault("stacklevel", 2)
    get_logger().error(msg, *args, **kwargs)
