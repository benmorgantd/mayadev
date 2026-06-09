# weights

import os
from xml.etree import ElementTree

import maya.cmds as cmds
import maya.api.OpenMaya as om

from bmaya.core.util import fileUtils
from bmaya.core import log


def get_joints_from_xml(weights_dir):
    tree = ElementTree.parse(weights_dir)
    root = tree.getroot()

    joints = []

    for child in root:
        if child.tag == "weights":
            joints.append(child.attrib["source"])

    return joints


def save(weights_dir):
    # Saves each selected object to a file in the given directory
    # with its nameUtils.

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    it_sel = om.MItSelectionList(sel)

    if not os.path.exists(weights_dir):
        os.makedirs(weights_dir)

    while not it_sel.isDone():
        dag = om.MDagPath()
        it_sel.getDagPath(dag)

        dag_name = str(dag.partialPathName())

        skin = cmds.ls(cmds.listHistory(dag_name), type="skinCluster") or []

        filename = os.path.join(weights_dir, dag_name + ".weights")
        if os.path.exists(filename):
            # version the file
            fileUtils.version_file(filename)

        if skin:
            # exports by vertex index. Changes to the vert order will break this
            # with the new 'format' argument, this might not be backwards
            # compatible... - _-
            cmds.deformerWeights(
                "{0}.weights".format(dag_name),
                deformer=skin[0],
                export=True,
                path=weights_dir,
                method="index",
                format="XML",
            )
        else:
            log.info(dag_name, " has no skin cluster to save.")
            it_sel.next()

        log.info("Saved weights for {}".format(dag_name))

        it_sel.next()


def load(weights_path):
    """Tries to load a single weights file onto a matching item in the scene"""

    if not os.path.exists(weights_path):
        raise ValueError("Given weights path doesn't exist")

    if not weights_path.endswith(".weights"):
        raise ValueError("Given file must be in .weights format")

    obj_name = os.path.basename(weights_path).replace(".weights", "")
    weights_dirname = os.path.dirname(weights_path)

    if not cmds.objExists(obj_name):
        om.MGlobal.displayInfo("{0} does not exist in scene.".format(obj_name))
        return

    log.info("Loading weights for <" + obj_name + "> ...")

    # look for and delete old clusters if they exist
    existing_skin_cluster = (
        cmds.ls(cmds.listHistory(obj_name), type="skinCluster") or []
    )

    if existing_skin_cluster:
        cmds.delete(existing_skin_cluster)

    joint_list = get_joints_from_xml(weights_path)

    cmds.select(cl=1)

    for jnt in joint_list:
        if not cmds.objExists(jnt):
            newJnt = cmds.joint(name=jnt)
            cmds.select(cl=1)

    cmds.select(joint_list)

    cmds.select(obj_name, add=True)

    # add the skin cluster
    # Add in options to load from previous saved skin cluster's settings since
    # we may not want 4 max influences or linear blending
    new_cluster = cmds.skinCluster(
        weightDistribution=1,
        obeyMaxInfluences=False,
        toSelectedBones=True,
        skinMethod=0,
        bindMethod=1,
    )

    cmds.deformerWeights(
        "{0}.weights".format(obj_name),
        im=True,
        path=weights_dirname,
        ignoreName=True,
        method="index",
        deformer=new_cluster[0],
    )
    cmds.select(obj_name)
    cmds.skinPercent(new_cluster[0], normalize=True)
    om.MGlobal.displayInfo("Loaded skinCluster weights onto {0}".format(obj_name))

    log.info("Weight data loaded from {0}".format(weights_path))
