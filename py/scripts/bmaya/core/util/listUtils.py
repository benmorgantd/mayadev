from typing import Any

def firstOrDefault(iterable: list, default: Any = None) -> Any:
    try:
        iterator = iter(iterable)
    except TypeError:
        raise TypeError("Given argument is not an iterable")

    return next(iterator, default)
