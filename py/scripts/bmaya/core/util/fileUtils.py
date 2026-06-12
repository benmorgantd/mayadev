"""Utilities related to working with files and versioning them."""

import os

import shutil
from bmaya.core import log


def version_file(filepath: str) -> None:
    """Saves off a copy of the given file to a <filename>.Versions folder.

    Args:
        filepath (str): The file to version.

    """

    if not os.path.exists(filepath):
        return

    dirname = os.path.dirname(filepath)

    filename, extension = os.path.splitext(os.path.basename(filepath))

    version_folder = os.path.join(dirname, (filename + ".Versions"))

    # create the version folder if it doesn't exist
    if not os.path.exists(version_folder):
        os.mkdir(version_folder)

    num_versions = len(os.listdir(version_folder))

    version_filename = os.path.join(
        version_folder, "{0}_{1:04d}{2}".format(filename, (num_versions + 1), extension)
    )

    shutil.copy(filepath, version_filename)

    log.info("Versioned file to {0}".format(version_filename))
