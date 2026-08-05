"""Logging wrapper for Maya, including handles for if we are in batch mode or not."""

import sys
import logging
# TODO: this is in core but we have maya imports here.
import maya.api.OpenMaya as om
import bmaya.maya.constants

_LOGGER = None

# LOG_FORMAT = "[%(levelname)s] %(asctime)s.%(msecs)02d %(filename)s:%(lineno)d >> %(message)s"
LOG_FORMAT = "[%(levelname)s] %(filename)s:%(lineno)d >> %(message)s"

# TODO: move this to a maya level module
class MayaLogHandler(logging.Handler):
    """Redirects standard Python logging records to native Maya GUI elements."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                om.MGlobal.displayError(msg)
            elif record.levelno >= logging.WARNING:
                om.MGlobal.displayWarning(msg)
            else:
                om.MGlobal.displayInfo(msg)
        except Exception:
            self.handleError(record)


def init_logger(is_batch=False) -> logging.Logger:
    """Explicitly initializes and configures the master bmaya logger."""
    global _LOGGER

    logger_name = "bmaya"
    _LOGGER = logging.getLogger(logger_name)

    # Keep the logger at DEBUG so it can capture all event types
    _LOGGER.setLevel(logging.DEBUG)

    for handler in _LOGGER.handlers[:]:
        _LOGGER.removeHandler(handler)

    # Set default visibility threshold for handlers to INFO
    default_handler_level = logging.INFO

    # Branch logging behavior for headless batch execution
    if is_batch:
        formatter = logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S")

        # Target sys.stdout so the framework's StreamTee can intercept it
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.setLevel(default_handler_level)
        _LOGGER.addHandler(stdout_handler)
    else:
        # Standard Interactive UI Configuration
        formatter = logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S")
        handler = MayaLogHandler()
        handler.setFormatter(formatter)
        handler.setLevel(default_handler_level)
        _LOGGER.addHandler(handler)

    _LOGGER.propagate = False
    return _LOGGER


def get_logger() -> logging.Logger:
    global _LOGGER
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
