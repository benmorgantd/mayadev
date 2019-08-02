
# rig tools library

import maya.mel as mel
import maya.cmds as cmds
import maya.OpenMaya as om

def snap_transforms(target, child):
  mel.eval("cycleCheck -e off;")
  try:
    p_const = cmds.pointConstraint(target, child, mo=0)
    # need to set this keyframe on the anim layer
    set_key(obj = child, attr="t", time=cmds.currentTime(query=True))
    cmds.delete(p_const)
  except RuntimeError:
    # translate locked
    pass
  try:
    cmds.setAttr(child + ".rx", 0)
    cmds.setAttr(child + ".ry", 0)
    cmds.setAttr(child + ".rz", 0)
    const = cmds.orientConstraint(target, child, mo=0)[0]
    cmds.setAttr(const + ".interpType", 2)
    set_key(obj = child, attr="r", time=cmds.currentTime(query=True))
    cmds.delete(const)
  except RuntimeError:
    # rotate locked
    pass
  mel.eval("cycleCheck -e on;")


def find_pole_vector(up_joint, mid_joint, low_joint, scale_factor=1):
  joints = om.MSelectionList()

  joints.add(up_joint)
  joints.add(mid_joint)
  joints.add(low_joint)

  up_joint_dag = om.MDagPath()
  mid_joint_dag = om.MDagPath()
  low_joint_dag = om.MDagPath()

  joints.getDagPath(0, up_joint_dag)
  joints.getDagPath(1, mid_joint_dag)
  joints.getDagPath(2, low_joint_dag)

  up_joint_fn_trans = om.MFnTransform(up_joint_dag)
  mid_joint_fn_trans = om.MFnTransform(mid_joint_dag)
  low_joint_fn_trans = om.MFnTransform(low_joint_dag)

  up_joint_vec = up_joint_fn_trans.getTranslation(om.MSpace.kWorld)
  mid_joint_vec = mid_joint_fn_trans.getTranslation(om.MSpace.kWorld)
  low_joint_vec = low_joint_fn_trans.getTranslation(om.MSpace.kWorld)

  # A - B gives us the vector from B to A
  up_low_vec = low_joint_vec - up_joint_vec
  up_mid_vec = mid_joint_vec - up_joint_vec

  # project the up_mid_vec onto the line made by up_low_vec
  projection = up_low_vec * ((up_mid_vec * up_low_vec) / (up_low_vec * up_low_vec))
  affine_projection = projection + up_joint_vec

  projection_through_mid_joint = (mid_joint_vec - affine_projection)
  # multiply by ((up_to_mid_vec.length() / projection_through_mid_joint)
  scaled_projection_through_mid_joint = projection_through_mid_joint * (
    up_mid_vec.length() / projection_through_mid_joint.length()) * scale_factor

  pole_vector_location = (affine_projection + scaled_projection_through_mid_joint)

  return [pole_vector_location.x, pole_vector_location.y, pole_vector_location.z]


def set_key(obj, attr, time):
  current_anim_layer = cmds.treeView("AnimLayerTabanimLayerEditor", query=True, selectItem=True)
  if current_anim_layer:
    cmds.setKeyframe("{0}.{1}".format(obj, attr), animLayer=current_anim_layer[0], time=time)
  else:
    cmds.setKeyframe("{0}.{1}".format(obj, attr), time=time)


def toggle_ikfk():
  # toggles the selected item between ik and fk mode if possible
  # we can find all the required info by going up to the item's module node! :D
  sel = cmds.ls(selection=True)
  if len(sel) == 1:
    # try to walk up to the module node
    try:
      module = cmds.listConnections("{0}.module".format(sel[0]), destination=True)[0]
    except IndexError:
      return False
    side = cmds.getAttr("{0}.side".format(module))
    module_type = cmds.getAttr("{0}.type".format(module))
    
    if module_type not in ["IkFkLeg", "IkFkArm"]:
      return False

    ik_switch_cc = cmds.listConnections("{0}.ikSwitch".format(module))[0]
    current_ikfk_value = cmds.getAttr("{0}.ikFk".format(ik_switch_cc))
    cmds.undoInfo(openChunk=True)
    set_key(obj = ik_switch_cc, attr="ikFk", time=(cmds.currentTime(query=True) - 1.0))
    cmds.setAttr("{0}.ikFk".format(ik_switch_cc), not current_ikfk_value)
    set_key(obj = ik_switch_cc, attr="ikFk", time=cmds.currentTime(query=True))

    # get the bind joints so we can derive the ik and fk joints from them
    upLimb = cmds.listConnections("{0}.startJoint".format(module))[0]
    loLimb = cmds.listConnections("{0}.midJoint".format(module))[0]
    endJoint = cmds.listConnections("{0}.endJoint".format(module))[0]

    if module_type == "IkFkLeg":
      # snap the fk toe control to the ik toe
      foot_module = cmds.listConnections("{0}.footModule".format(endJoint))[0]
      fk_toe = cmds.listConnections("{0}.fkToe".format(foot_module))[0]
      ik_toe = cmds.listConnections("{0}.ikToe".format(foot_module))[0]

    if not current_ikfk_value:
      # IK --> FK (snap fk to ik)
      snap_transforms(target=cmds.listConnections("{0}.ik".format(upLimb))[0], child=cmds.listConnections("{0}.component".format(upLimb))[0])
      snap_transforms(target=cmds.listConnections("{0}.ik".format(loLimb))[0], child=cmds.listConnections("{0}.component".format(loLimb))[0])
      snap_transforms(target=cmds.listConnections("{0}.ik".format(endJoint))[0], child=cmds.listConnections("{0}.component".format(endJoint))[0])

      if module_type == "IkFkLeg":
        # get toe control
        snap_transforms(target=ik_toe, child=fk_toe.replace("_rig", "") + "_cc")

    else:
      # FK --> IK (snap ik to fk)
      # it's actually important that we mov the ik control before the pole vector control.
      # that way, regradless of what the follow attribute is at, it will be put in the right world position
      snap_transforms(target=cmds.listConnections("{0}.fk".format(endJoint))[0], child=cmds.listConnections("{0}.ikControl".format(module))[0])    
      pv_cc = cmds.listConnections("{0}.ikPoleVectorControl".format(module))[0]
      cmds.xform(pv_cc, t=find_pole_vector(cmds.listConnections("{0}.fk".format(upLimb))[0], 
                                           cmds.listConnections("{0}.fk".format(loLimb))[0], 
                                           cmds.listConnections("{0}.fk".format(endJoint))[0], scale_factor=1.6), worldSpace=True)
      
      set_key(obj=pv_cc, attr="t", time=cmds.currentTime(query=True))
      
      if module_type == "IkFkLeg":
        # special condition for matching toe bend
        cmds.setAttr("{0}.toeBend".format(cmds.listConnections("{0}.ikControl".format(module))[0]), cmds.getAttr("{0}.rz".format(fk_toe)) / 4.5)

    cmds.undoInfo(closeChunk=True)
    return True

  else:
    self.menu.hide()
    return Fals
