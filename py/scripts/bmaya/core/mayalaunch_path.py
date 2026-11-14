"""Puts the mayalaunch package on sys.path. Import this module, then import mayalaunch.

mayalaunch is a separate repo shared with RigModules: it is the one place that starts Maya and ends it safely.
It is found through MAYALAUNCH_ROOT (the folder that holds the `mayalaunch` package), else a sibling folder
named mayalaunch beside any parent of this file. RigModules has the same finder in tools/mayalaunch_path.py:
it has to run before mayalaunch can be imported, so mayalaunch can't hold it.
"""
import os
import sys

ROOT_VARIABLE = "MAYALAUNCH_ROOT"


def find_root():
    candidates = [os.environ.get(ROOT_VARIABLE)]
    folder = os.path.dirname(os.path.abspath(__file__))
    while True:
        candidates.append(os.path.join(folder, "mayalaunch"))
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    for candidate in candidates:
        if candidate and os.path.isfile(os.path.join(candidate, "mayalaunch", "__init__.py")):
            return candidate
    raise ImportError("mayalaunch not found. Set %s to the folder that holds the mayalaunch package." % ROOT_VARIABLE)


_root = find_root()
if _root not in sys.path:
    sys.path.insert(0, _root)
