import os
import xml.etree.ElementTree as et
import maya.cmds as cmds
import maya.api.OpenMaya as om


def parse_xml(filepath):
    tree = et.parse(filepath)
    root = tree.getroot()

    joints = []

    for child in root:
        if child.tag == "weights":
            joints.append(child.attrib["source"])

    return joints


def export_weights(
        path=r"D:/Documents/Google Drive/01 BFA/Thesis Project Local Files/Rig/skin_library/Alpha/"):

    # export each selected object to the selected path
    for obj in cmds.ls(selection=True):
        skin_cluster = cmds.ls(cmds.listHistory(obj), type="skinCluster")
        if skin_cluster and len(skin_cluster):
            # exports by vertex index. Changes to the vert order will break
            # this
            cmds.deformerWeights(
                "{0}.weights".format(obj),
                path=path,
                export=True,
                method="index",
                deformer=skin_cluster[0])
            om.MGlobal.displayInfo("Exported weights from {0}..".format(obj))

# export_weights()


def import_weights(
        path=r"D:/Documents/Google Drive/01 BFA/Thesis Project Local Files/Rig/skin_library/Alpha/"):
    original_selection = cmds.ls(selection=True)
    # import the weights for each selected object.
    for obj in original_selection:
        # check if there's a skin file available at the path for an object that
        # matches that name
        filename = "{0}{1}.weights".format(path, obj)

        if os.path.isfile(filename):
            # get information for the skin cluster from the xml file so that we
            # can use it to build the new skinCluster on this obj
            joint_list = parse_xml(filename)

            # look for and delete old clusters if they exist
            old_cstr = cmds.ls(cmds.listHistory(obj), type="skinCluster")

            if len(old_cstr):
                cmds.delete(old_cstr)

            cmds.select(joint_list)

            cmds.select(obj, add=1)

            # add the skin cluster
            new_cstr = cmds.skinCluster(maximumInfluences=4,
                                        weightDistribution=1,
                                        obeyMaxInfluences=True,
                                        toSelectedBones=True,
                                        skinMethod=0,
                                        bindMethod=1)

            cmds.deformerWeights(
                "{0}.weights".format(obj),
                im=True,
                path=path,
                ignoreName=True,
                method="index",
                deformer=new_cstr[0])
            cmds.select(obj)
            cmds.skinPercent(new_cstr[0], normalize=True)
            om.MGlobal.displayInfo(
                "Loaded skinCluster weights onto {0}".format(obj))

        else:
            om.MGlobal.displayError(
                "Weights file doesn't exist for {0}".format(obj))

    cmds.select(original_selection)


# import_weights()
