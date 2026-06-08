import logging
import sys
import maya.api.OpenMaya as om

# Global logger instance variable, initialized as None
_LOGGER = None


class MayaLogHandler(logging.Handler):
    """Redirects standard Python logging records to native Maya GUI elements."""

    def emit(self, record):

        try:
            msg = self.format(record)

            if record.levelno >= logging.ERROR:
                om.MGlobal.DisplayError(msg)

            elif record.levelno >= logging.WARNING:
                om.MGlobal.displayWarning(msg)

            else:
                om.MGlobal.displayInfo(msg)

        except Exception:
            self.handleError(record)


def init_logger():
    """Explicitly initializes and configures the master bmaya logger.

    Call this on startup (e.g., in userSetup.py) to activate logging.
    """

    global _LOGGER

    logger_name = "bmaya"

    _LOGGER = logging.getLogger(logger_name)

    _LOGGER.setLevel(logging.DEBUG)

    # Prevent duplicate handlers if called multiple times

    for handler in _LOGGER.handlers[:]:
        if isinstance(handler, MayaLogHandler):
            _LOGGER.removeHandler(handler)

    log_format = "[%(name)s][%(filename)s:%(lineno)d] %(message)s"

    formatter = logging.Formatter(log_format)

    handler = MayaLogHandler()

    handler.setFormatter(formatter)

    _LOGGER.addHandler(handler)

    _LOGGER.propagate = False

    info("Initialized logger")

    return _LOGGER


def get_logger():
    """Returns the active logger instance, initializing a fallback if not yet setup."""

    global _LOGGER

    if _LOGGER is None:
        # Fallback to prevent attribute errors if someone imports and uses a
        # log

        # method before init_logger() has been explicitly invoked.

        return init_logger()

    return _LOGGER


# ----------------------------------------------------------------------
# Public API Aliases
# ----------------------------------------------------------------------


def info(msg, *args, **kwargs):

    get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):

    get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):

    if "exc_info" not in kwargs and sys.exc_info()[0] is not None:
        kwargs["exc_info"] = True

    get_logger().error(msg, *args, **kwargs)
