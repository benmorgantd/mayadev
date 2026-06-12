"""General decorators for pure python and a function to create a decorator out of a function"""

import time
from functools import wraps

from . import log


def decorator_maker(meta_decorator):
    """
    A base decorator that wraps a function, transforming it into
    a reusable decorator that preserves metadata cleanly.

    Wrap a generic function in this to make it a decorator.
    The fn must have the args (func, *args, **kwargs) and return the result. It can do things
    then before and after executing the result.
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

    log.info(f"[TIMER] '{func.__name__}' took {execution_time:.6f} seconds to execute.")
    return result
