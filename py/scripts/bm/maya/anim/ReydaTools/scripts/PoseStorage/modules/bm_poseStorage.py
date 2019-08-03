import maya.cmds as cmds
import os
import errno
import json

"""
Pose Storage v02

A pose library system for reading and writing "poses". 

- Create poses by selecting controls and running "write_pose" (will strip the namespace from those controls)
    - Makes a .pose file in the directory you've chosen.
    
- Read poses by running "read_pose" (needs to be supplied a namespace if one exists)

Version 2:
- pep8 formatting
- updating
"""

# Global variable that stores the full path to our script
SCRIPT_LOC = os.path.split(__file__)[0]
POSES_DIR_NAME = "poses"


##############
# Pose Class #
##############


class Pose(object):
    def __init__(self, pose_file, is_full_path=True):
        """Pose objects hold the file data from a .pose file.

        :param pose_file: the short name or full path to a .pose file
        :param is_full_path: Boolean to determine if the pose_file should be treated as a full path
        """


        # check to make sure it's a pose file
        if not pose_file.endswith(".pose"):
            raise RuntimeError("Pose_file must be a .pose pose_file.")
        # we'll use a dictionary to hold the file's pose data
        self.pose_data = {}
        self.pose_file = pose_file

        if not is_full_path:
            # this bit is leftover from before this was made with a UI.
            try:
                file_str = open(os.path.join(SCRIPT_LOC, POSES_DIR_NAME, self.pose_file), "r")
            except IOError:
                print "Pose file does not exist. Is it in this script's directory?"
                return
        else:
            # with the ui, everything is done with full paths
            try:
                file_str = open(self.pose_file, "r")
            except IOError:
                print "Pose file does not exist. Is it in this script's directory?"
                return

        # read the json file
        self.file_data = json.loads(file_str.read())

        # Load that data into our self.pose_data dictionary
        for ctrl in self.file_data:
            # each control has a dictionary of its attributes
            self.pose_data[ctrl] = {}
            for attr in self.file_data[ctrl]:
                # each attribute has a corresponding value
                self.pose_data[ctrl][attr] = self.file_data[ctrl][attr]

        file_str.close()


#####################
# Pose Master Class #
#####################

class PoseMaster(object):
    def __init__(self, root_dir=None):
        """The PoseMaster object is used to read, write, and load pose files.
        We do this to minimize the amount of file io that has to be done

        :param root_dir: Full path to the root directory to use
        """
        self.pose_objects = {}
        if not root_dir:
            return
        self.root_dir = root_dir
        # The files will only get read when the PoseMaster object gets created

    def write_pose(self, pose_name=None, is_full_path=True):
        """Writes a json file (.pose) that stores the attribute values for each selected object.

        :param pose_name: The name for the pose file
        :param is_full_path: Determines if the pose_name will be treated as a full path
        :return:
        """
        # Get our selection, since we're storing the attributes and values for every selected object

        # strip the namespaces from the objects
        # tmp_sel objects still might have their namespaces in them
        tmp_sel = cmds.ls(sl=1)
        namespace = ""

        sel = []
        for obj in tmp_sel:
            if ":" in obj:
                # Strip the namespace from the object before storing if it has one.
                namespace = obj[0:obj.index(":")]
                sel.append(obj[obj.index(":") + 1:])
            else:
                sel.append(obj)
        if not is_full_path:
            # Create a new .pose pose_file in our poses directory
            f = open(os.path.join(SCRIPT_LOC, POSES_DIR_NAME, pose_name + ".pose"), "w")
        else:
            f = open(pose_name, "w")

        # Our pose dictionary contains the attributes and values for every selected object
        pose = {}
        for obj in sel:
            attributes = cmds.listAttr(namespace + ":" + obj, k=1)
            # Make a key for each object, and at that key add a new dictionary
            pose[obj] = {}
            if attributes:
                for attr in attributes:
                    # Store the attributes and their corresponding values in that object's dictionary entry
                    pose[obj][attr] = cmds.getAttr(namespace + ":" + obj + ".%s" % attr)

        # Do a pretty dump of the dictionary into a json format
        json_text = json.dumps(pose, sort_keys=True, indent=4, separators=(",", " : "))
        f.write(json_text)
        f.close()

        # Add our new pose to the array of pose objects
        self.pose_objects[pose_name + ".pose"] = Pose(pose_name + ".pose")

    def read_pose(self, pose_name=None, namespace="", multiplier=0.2, ctrl_pressed=False, shift_pressed=False, alt_pressed=False):
        """Reads the data from a .pose json file.

        :param pose_name: The full path to the pose. Used as the key for our pose_objects dictionary.
        :param selection_only: Boolean to only apply this to the selected objects.
        :param namespace: The namespace to use when applying this pose. Will append ":" to the end if it's not in it.
        :return:
        """

        cmds.undoInfo(openChunk=True)

        # First go through our pose objects array and see if that pose has already been loaded there.
        exists = False
        for pose_object in self.pose_objects:
            if pose_name == pose_object:
                pose_data = self.pose_objects[pose_name].pose_data
                exists = True
        if not exists:
            raise IOError("{0}.pose does not exist in this script's directory.".format(pose_name))

        if alt_pressed:
            cmds.select(["{0}:{1}".format(namespace, ctrl) for ctrl in pose_data], replace=True)
            return

        sel = cmds.ls(sl=1)
        
        for ctrl in pose_data:
            # Now go through every attribute at the control's index in the dictionary
            for attr in pose_data[ctrl]:
                # Get the attribute's value
                val = pose_data[ctrl][attr]

                # The priority here are floats since Maya would accept (1.0) as a boolean argument.
                # Everything else in Maya (enum attributes, etc) are stored as indexes, not string values.
                try:
                    float_val = float(val)
                    try:
                        if ctrl_pressed:
                            current_value = cmds.getAttr("{0}:{1}.{2}".format(namespace, ctrl, attr))
                            try:
                                if "scale" not in attr:
                                    cmds.setAttr("{0}:{1}.{2}".format(namespace, ctrl, attr), current_value + (float_val * multiplier))
                                else:
                                    cmds.setAttr("{0}:{1}.{2}".format(namespace, ctrl, attr), current_value + ((float_val - 1) * multiplier))
                            except RuntimeError:
                                # locked attr
                                pass
                        elif shift_pressed:
                            current_value = cmds.getAttr("{0}:{1}.{2}".format(namespace, ctrl, attr))
                            try:
                                if "scale" not in attr:
                                    cmds.setAttr("{0}:{1}.{2}".format(namespace, ctrl, attr), current_value - (float_val * multiplier))
                                else:
                                    cmds.setAttr("{0}:{1}.{2}".format(namespace, ctrl, attr), current_value - ((float_val - 1) * multiplier))
                            except RuntimeError:
                                # locked attr
                                pass
                        else:
                            try:
                                cmds.setAttr("{0}:{1}.{2}".format(namespace, ctrl, attr), float_val)
                            except RuntimeError:
                                pass
                    # We do this to catch the error caused by the object not existing in the scene.
                    except RuntimeError:
                        print "Error: " + namespace + ctrl + " does not exist in scene."
                        break
                except ValueError:
                    try:
                        bool_val = bool(val)
                        cmds.setAttr("{0}:{1}.{2}".format(namespace, ctrl, attr), bool_val)
                    except ValueError:
                        continue

        cmds.undoInfo(closeChunk=True)

    def load_poses(self, folder):
        """Initiates every .pose file in "folder" as a Pose object.

        :param folder: The full path to the folder to search.
        :return: None
        """
        # Ran at the beginning and on refreshes.

        # Attempt to create POSES_DIR_NAME directory, if it doesn't exist yet.
        # (Code magic done by Justin)
        try:
            os.makedirs(folder)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Creates an array of pose objects that contain the data of our .pose files.
        try:
            for pose_file in os.listdir(folder):
                if pose_file.endswith(".pose"):
                    full_path = os.path.join(folder, pose_file)
                    self.pose_objects[full_path] = Pose(full_path)
        except OSError:
            print "Error: Path directory " + folder + " is inaccessible."


def list_poses(root_dir=SCRIPT_LOC):
    """Used to find the pose files in each subfolder from the root directory. Will not return folders
    that do not contain any pose files in them.

    :param root_dir: the directory to start searching from. Will search each subdirectory
    :return: Dictionary containing full paths to the folder and it's corresponding .pose files.
    """


    pose_folder_and_files = {}
    this_folder_files = []
    # print "\nListing .pose files..."
    # First find any pose files in the root directory

    print "Root Directory:" , root_dir

    if not os.path.isdir(root_dir):
        return

    for f in os.listdir(root_dir):
        if f.endswith(".pose"):
            this_folder_files.append(os.path.join(SCRIPT_LOC, f))
    if len(this_folder_files) > 0:
        pose_folder_and_files[root_dir] = this_folder_files

    # Second, go through each subdirectory
    for folder in os.walk(root_dir):
        this_folder_files = []
        for f in os.listdir(folder[0]):
            if f.endswith(".pose"):
                file_full_path = os.path.join(folder[0], f)
                # print f
                this_folder_files.append(file_full_path)
        if len(this_folder_files) > 0:
            pose_folder_and_files[folder[0]] = this_folder_files

    return pose_folder_and_files
