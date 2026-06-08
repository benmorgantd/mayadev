import time
from functools import wraps

from . import log


def decorator_maker(meta_decorator):
    """
    A base decorator that wraps a function, transforming it into 
    a reusable decorator that preserves metadata cleanly.
    """
    @wraps(meta_decorator)
    def decorator_transformer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return meta_decorator(func, *args, **kwargs)
        return wrapper
    return decorator_transformer


@decorator_maker
def log_fn_duration(func, *args, **kwargs):
    """
    Measures the execution time of a function and prints the duration.
    """
    start_time = time.perf_counter()

    # Execute the target function
    result = func(*args, **kwargs)

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    log.info(
        f"[TIMER] '{func.__name__}' took {execution_time:.6f} seconds to execute.")
    return result
