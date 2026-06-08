"""Purpose:
Gives the logic for saving and loading the build component, which is a json file that contains the rig structure.
"""

import json
import os


def load(filepath):

    if not os.path.exists(filepath):
        raise RuntimeError('Filepath does not exist.')

    with open(filepath, "r") as f:
        build_data = json.load(f)

    return build_data


def save(filepath, data):

    if not os.path.exists(os.path.dirname(filepath)):
        raise RuntimeError('Filepath does not exist.')

    with open(filepath, "w+") as f:
        json.dump(data, f, separators=(', ', ':'), indent=2, sort_keys=True)
