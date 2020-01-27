import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Mothbitch(Gossamer.creator.Creator):
  """Character creator class for the Mothbitch rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Mothbitch"):
    super(Mothbitch, self).__init__(char_name=char_name)
    
  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    self.make_SingleJoint(joint="pelvis", module_name="Pelvis", side="c", control_shape="Cube")

    # Spine
    self.make_FkChain(joints=["spine1", "spine2", "chest"], module_name="Spine", side="c")

    # Neck and Head
    self.make_SingleJoint(joint="neck", module_name="Neck", side="c", control_shape="Cylinder")
    self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")

    self.make_SingleJoint(joint="LF_eye", module_name="LF_eye", side="LF", control_shape="Square")
    cmds.connectAttr("LF_eye_cc.scale", "LF_eye.scale")
    self.make_SingleJoint(joint="RT_eye", module_name="RT_eye", side="RT", control_shape="Square")
    cmds.connectAttr("RT_eye_cc.scale", "RT_eye.scale")

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")

    # Legs
    LF_leg = self.make_IkFkLeg(joints=["LF_upLeg", "LF_loLeg", "LF_foot"], module_name="LF_Leg", side="LF")
    RT_leg = self.make_IkFkLeg(joints=["RT_upLeg", "RT_loLeg", "RT_foot"], module_name="RT_Leg", side="RT")

    # Arms
    LF_arm = self.make_IkFkArm(joints=["LF_upArm", "LF_loArm", "LF_wrist"], module_name="LF_Arm", side="LF")
    RT_arm = self.make_IkFkArm(joints=["RT_upArm", "RT_loArm", "RT_wrist"], module_name="RT_Arm", side="RT")
    
    # Twist extraction via Quat and scIK extraction depending on where it works better.
    self.make_QuatTwist(module_name="LF_loArm_twist", side="LF", extract_joint="LF_wrist_drive", twist_joints=["LF_loArmTwist_01"], multiplier=.5)
    self.make_QuatTwist(module_name="RT_loArm_twist", side="RT", extract_joint="RT_wrist_drive", twist_joints=["RT_loArmTwist_01"], multiplier=.5)
    
    self.make_QuatTwist(module_name="LF_loLeg_twist", side="LF", extract_joint="LF_loLeg_drive", twist_joints=["LF_loLegTwist_01"], multiplier=-.5)
    self.make_QuatTwist(module_name="RT_loLeg_twist", side="RT", extract_joint="RT_loLeg_drive", twist_joints=["RT_loLegTwist_01"], multiplier=.5)

    self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="head", twist_joints=["neckTwist_01"], multiplier=.5)
    
    self.make_IkTwist(module_name="LF_upLeg_twist", side="LF", extract_joint="LF_upLeg_drive", start_joint="LF_loLeg_drive", twist_joints=["LF_upLegTwist_01", "LF_upLegTwist_02", "LF_upLegTwist_03"], ik_parent="pelvis")
    self.make_IkTwist(module_name="RT_upLeg_twist", side="RT", extract_joint="RT_upLeg_drive",  start_joint="RT_loLeg_drive",twist_joints=["RT_upLegTwist_01", "RT_upLegTwist_02", "RT_upLegTwist_03"], ik_parent="pelvis")

    self.make_IkTwist(module_name="LF_upArm_twist", side="LF", extract_joint="LF_upArm_drive", start_joint="LF_loArm_drive", twist_joints=["LF_upArmTwist_01", "LF_upArmTwist_02", "LF_upArmTwist_03"], ik_parent="LF_clavicle")
    self.make_IkTwist(module_name="RT_upArm_twist", side="RT", extract_joint="RT_upArm_drive", start_joint="RT_loArm_drive", twist_joints=["RT_upArmTwist_01", "RT_upArmTwist_02", "RT_upArmTwist_03"], ik_parent="RT_clavicle")

    # hood
    self.make_SingleJoint(joint="hood_tip", side="c", module_name="HoodTip", control_shape="Cube")
    self.make_SingleJoint(joint="spool", side="", module_name="Spool", control_shape="Cylinder")

    # ears
    self.make_FkChain(joints=["LF_ear1", "LF_ear2"], side="LF", module_name="LF_ear")
    self.make_FkChain(joints=["RT_ear1", "RT_ear2"], side="RT", module_name="RT_ear")

    # Fingers
    self.make_FkChain(module_name="LF_index", side="LF", joints=["LF_index1","LF_index2","LF_index3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_mid", side="LF", joints=["LF_mid1","LF_mid2","LF_mid3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_ring", side="LF", joints=["LF_ring1","LF_ring2","LF_ring3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_pinkie", side="LF", joints=["LF_pinkie1","LF_pinkie2","LF_pinkie3","LF_pinkie4"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_thumb", side="LF", joints=["LF_thumb1","LF_thumb2","LF_thumb3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")

    self.make_FkChain(module_name="RT_index", side="RT", joints=["RT_index1","RT_index2","RT_index3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_mid", side="RT", joints=["RT_mid1","RT_mid2","RT_mid3",], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_ring", side="RT", joints=["RT_ring1","RT_ring2","RT_ring3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_pinkie", side="RT", joints=["RT_pinkie1","RT_pinkie2","RT_pinkie3","RT_pinkie4"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_thumb", side="RT", joints=["RT_thumb1","RT_thumb2","RT_thumb3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")


    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Mothbitch_grp")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      if "eye_cc" not in obj:
        cmds.setAttr(obj + ".sx", lock=True, keyable=False, cb=0)
        cmds.setAttr(obj + ".sy", lock=True, keyable=False, channelBox=False)
        cmds.setAttr(obj + ".sz", lock=True, keyable=False, channelBox=False)

    cmds.select(cl=1)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

