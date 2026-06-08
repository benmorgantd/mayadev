

def firstOrDefault(iterable, default=None):
    try:
        iterator = iter(iterable)
    except TypeError:
        raise TypeError("Given argument is not an iterable")

    return next(iterator, default)
