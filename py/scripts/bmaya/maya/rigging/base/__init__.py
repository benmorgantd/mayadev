import os

dirname = os.path.dirname(os.path.abspath(__file__))

__all__ = [
    mod[0:-3]
    for mod in os.listdir(dirname)
    if mod.endswith(".py") and mod != "__init__.py"
]
