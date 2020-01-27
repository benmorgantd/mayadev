import maya.cmds as cmds

cmds.loadPlugin("quatNodes", quiet=1)
cmds.loadPlugin("matrixNodes", quiet=1)
cmds.loadPlugin("fbxmaya", quiet=1)


def ik_twist_extract(twist_joint=None, start_joint=None, ik_parent=None, twist_joint_parent=None, name=None):
    dup1 = cmds.duplicate(twist_joint_parent, parentOnly=True, name=name + "_twist")[0]
    dup2 = cmds.duplicate(twist_joint_parent, parentOnly=True, name=name + "_twistEnd")[0]

    cmds.delete(cmds.parentConstraint(start_joint, dup1, mo=0))
    cmds.parent(dup2, dup1)

    ik = cmds.ikHandle(sj=dup1, ee=dup2, solver="ikSCsolver", name=name + "_scik_handle")

    cmds.parent(dup1, twist_joint)
    if ik_parent:
        cmds.parent(ik[0], ik_parent)

    cmds.hide(ik[0])
    cmds.hide(dup1)

    return [dup1, ik]


def quat_twist_extract(sel=None, axis="X"):
    # quat twistExtractor
    if not sel:
        try:
            sel = cmds.ls(sl=1)[0]
        except IndexError:
            raise IndexError("No object selected.")

    mm = cmds.createNode("multMatrix", n=sel.rstrip("_jj") + "_multMatrix")
    cmds.connectAttr(sel + ".worldMatrix[0]", mm + ".matrixIn[0]")
    cmds.connectAttr(sel + ".parentInverseMatrix[0]", mm + ".matrixIn[1]")

    decomp = cmds.createNode("decomposeMatrix", n=sel.rstrip("_jj") + "_decompMatrix")
    cmds.connectAttr(mm + ".matrixSum", decomp + ".inputMatrix")

    quatToEuler = cmds.createNode("quatToEuler", n=sel.rstrip("_jj") + "_quatToEuler")
    cmds.connectAttr("{0}.outputQuat{1}".format(decomp, axis), "{0}.inputQuat{1}".format(quatToEuler, axis))
    cmds.connectAttr(decomp + ".outputQuatW", quatToEuler + ".inputQuatW")
    cmds.connectAttr(sel + ".rotateOrder", quatToEuler + ".inputRotateOrder")

    return quatToEuler
