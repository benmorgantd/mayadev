import os
import sys
import logging
import maya.api.OpenMaya as om
import bmaya.maya.constants

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
    """Explicitly initializes and configures the master bmaya logger."""
    global _LOGGER

    logger_name = "bmaya"
    _LOGGER = logging.getLogger(logger_name)
    _LOGGER.setLevel(logging.DEBUG)

    for handler in _LOGGER.handlers[:]:
        _LOGGER.removeHandler(handler)

    # Branch logging behavior for headless batch execution
    #if os.environ.get("BMAYA_BATCH_MODE") == "1":
    if bmaya.maya.constants.IS_BATCH:
        log_format = "[%(name)s][%(asctime)s.%(msecs)02d][%(filename)s:%(lineno)d] %(message)s"
        formatter = logging.Formatter(log_format, datefmt="%H:%M:%S")
        
        # Target sys.stdout so the framework's StreamTee can intercept it
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        _LOGGER.addHandler(stdout_handler)
    else:
        # Standard Interactive UI Configuration
        log_format = "[%(name)s][%(asctime)s.%(msecs)02d][%(filename)s:%(lineno)d] %(message)s"
        formatter = logging.Formatter(log_format, datefmt="%H:%M:%S")
        handler = MayaLogHandler()
        handler.setFormatter(formatter)
        _LOGGER.addHandler(handler)

    _LOGGER.propagate = False
    return _LOGGER

def get_logger():
    global _LOGGER
    if _LOGGER is None:
        return init_logger()
    return _LOGGER

def info(msg, *args, **kwargs):
    kwargs.setdefault("stacklevel", 2)
    get_logger().info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    kwargs.setdefault("stacklevel", 2)
    get_logger().warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    if "exc_info" not in kwargs and sys.exc_info()[0] is not None:
        kwargs["exc_info"] = True
    kwargs.setdefault("stacklevel", 2)
    get_logger().error(msg, *args, **kwargs)