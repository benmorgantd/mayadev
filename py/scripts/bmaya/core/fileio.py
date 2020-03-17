import os
import shutil


def versionFile(filepath):
    """Saves off a copy of the given file to a <filename>.Versions folder.
    
    Args:
        filepath (str): The file to version.
    
    """

    if not os.path.exists(filepath):
        return

    dirname = os.path.dirname(filepath)

    filename, extension = os.path.splitext(os.path.basename(filepath))

    versionFolder = os.path.join(dirname, (filename + ".Versions"))

    # create the version folder if it doesn't exist
    if not os.path.exists(versionFolder):
        os.mkdir(versionFolder)

    numVersions = len(os.listdir(versionFolder))

    versionFilename = os.path.join(versionFolder, "{0}_{1:04d}{2}".format(
        filename, (numVersions + 1), extension))

    shutil.copy(filepath, versionFilename)

    print "Versioned file to {0}".format(versionFilename)