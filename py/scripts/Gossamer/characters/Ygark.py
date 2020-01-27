import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Ygark(Gossamer.creator.Creator):
  """Character creator class for the Ygark rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Ygark"):
    super(Ygark, self).__init__(char_name=char_name)

  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    cmds.delete(all=True, channels=True, unitlessAnimationCurves=False)

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

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")

    # Legs
    LF_leg = self.make_IkFkLeg(joints=["LF_upLeg", "LF_loLeg", "LF_foot"], module_name="LF_Leg", side="LF")
    RT_leg = self.make_IkFkLeg(joints=["RT_upLeg", "RT_loLeg", "RT_foot"], module_name="RT_Leg", side="RT")

    # Arms
    LF_arm = self.make_IkFkArm(joints=["LF_upArm", "LF_loArm", "LF_wrist"], module_name="LF_Arm", side="LF")
    RT_arm = self.make_IkFkArm(joints=["RT_upArm", "RT_loArm", "RT_wrist"], module_name="RT_Arm", side="RT")

    # Feet
    self.make_Foot(joints=["LF_foot", "LF_toe", "LF_toeTip"], locs=["LF_heel", "LF_bankIn_loc", "LF_bankOut_loc"], module_name="LF_Foot", side="LF")
    self.make_Foot(joints=["RT_foot", "RT_toe", "RT_toeTip"], locs=["RT_heel", "RT_bankIn_loc", "RT_bankOut_loc"], module_name="RT_Foot", side="RT")

    # (Fix for foot module fk visibility switching)
    cmds.connectAttr("LF_leg_ikSwitch_cc.ikFk", "LF_toe_fk_ccShape.v")
    cmds.connectAttr("RT_leg_ikSwitch_cc.ikFk", "RT_toe_fk_ccShape.v")

    # heel and toe tip adjustment controls
    self.make_SingleJoint(joint="LF_heel", module_name="LF_heel", side="LF", control_shape="Circle", child_of="pelvis_cc", constrained_to="LF_foot_rig_drive")
    self.make_SingleJoint(joint="RT_heel", module_name="RT_heel", side="RT", control_shape="Circle", child_of="pelvis_cc", constrained_to="RT_foot_rig_drive")

    self.make_SingleJoint(joint="LF_toeTip", module_name="LF_toeTip", side="LF", control_shape="Circle", child_of="pelvis_cc", constrained_to="LF_toe_rig_drive")
    self.make_SingleJoint(joint="RT_toeTip", module_name="RT_toeTip", side="RT", control_shape="Circle", child_of="pelvis_cc", constrained_to="RT_toe_rig_drive")

    # Twist extraction via Quat and scIK extraction depending on where it works better.
    self.make_QuatTwist(module_name="LF_loArm_twist", side="LF", extract_joint="LF_wrist_drive", 
                        twist_joints=["LF_loArmTwist_01"], 
                        limb_module=LF_arm.node)

    self.make_QuatTwist(module_name="RT_loArm_twist", side="RT", extract_joint="RT_wrist_drive",
                        twist_joints=["RT_loArmTwist_01", "RT_loArmTwist_02", "RT_loArmTwist_03"],
                        limb_module=RT_arm.node, multiplier=.5)
    
    self.make_QuatTwist(module_name="LF_loLeg_twist", side="LF", extract_joint="LF_foot_drive", twist_joints=["LF_loLegTwist_01", "LF_loLegTwist_02", "LF_loLegTwist_03"], axis="Y", multiplier=-1)
    self.make_QuatTwist(module_name="RT_loLeg_twist", side="RT", extract_joint="RT_foot_drive", twist_joints=["RT_loLegTwist_01", "RT_loLegTwist_02", "RT_loLegTwist_03"], axis="Y", multiplier=.85)

    self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="head", twist_joints=["neckTwist_01"], multiplier=.5)
    
    self.make_IkTwist(module_name="LF_upLeg_twist", side="LF", extract_joint="LF_upLeg_drive", start_joint="LF_loLeg_drive", twist_joints=["LF_upLegTwist_01", "LF_upLegTwist_02", "LF_upLegTwist_03"], ik_parent="pelvis")
    self.make_IkTwist(module_name="RT_upLeg_twist", side="RT", extract_joint="RT_upLeg_drive",  start_joint="RT_loLeg_drive",twist_joints=["RT_upLegTwist_01", "RT_upLegTwist_02", "RT_upLegTwist_03"], ik_parent="pelvis")

    self.make_IkTwist(module_name="LF_upArm_twist", side="LF", extract_joint="LF_upArm_drive", start_joint="LF_loArm_drive", twist_joints=["LF_upArmTwist_01", "LF_upArmTwist_02", "LF_upArmTwist_03"], ik_parent="LF_clavicle")
    self.make_IkTwist(module_name="RT_upArm_twist", side="RT", extract_joint="RT_upArm_drive", start_joint="RT_loArm_drive", twist_joints=["RT_upArmTwist_01", "RT_upArmTwist_02", "RT_upArmTwist_03"], ik_parent="RT_clavicle")

    # Fingers
    self.make_FkChain(module_name="LF_index", side="LF", joints=["LF_index01","LF_index02","LF_index03"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="LF_mid", side="LF", joints=["LF_mid01","LF_mid02","LF_mid03"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="LF_ring", side="LF", joints=["LF_ring01","LF_ring02","LF_ring03"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="LF_pinkie", side="LF", joints=["LF_pinkie01","LF_pinkie02","LF_pinkie03","LF_pinkie04"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="LF_thumb", side="LF", joints=["LF_thumb01","LF_thumb02","LF_thumb03"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive", control_shape="Sphere")

    self.make_FkChain(module_name="RT_index", side="RT", joints=["RT_index01","RT_index02","RT_index03"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="RT_mid", side="RT", joints=["RT_mid01","RT_mid02","RT_mid03"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="RT_ring", side="RT", joints=["RT_ring01","RT_ring02","RT_ring03"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="RT_pinkie", side="RT", joints=["RT_pinkie01","RT_pinkie02","RT_pinkie03","RT_pinkie04"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive", control_shape="Sphere")
    self.make_FkChain(module_name="RT_thumb", side="RT", joints=["RT_thumb01","RT_thumb02","RT_thumb03"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive", control_shape="Sphere")


    # tool
    tool = self.make_SingleJoint(joint="tool",module_name="Pistol", side=None, control_shape="Cylinder", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    tool.setup_multi_follow(control="tool_cc", targets=["RT_wrist", "LF_wrist"], module=tool.node)
    self.make_SingleJoint(joint="trigger", module_name="Trigger", side=None, control_shape="Cube")
    self.make_SingleJoint(joint="tool_end", module_name="ToolEnd", side=None, control_shape="Cube")

    # helmet
    self.make_SingleJoint(joint="helmet", module_name="Helmet", side="c", control_shape="Sphere")
    cmds.addAttr("root_cc", longName="Show_Helmet", at="long", dv=0, min=0, max=1, k=1)
    cmds.connectAttr("root_cc.Show_Helmet", "helmet_geo.v")
    cmds.connectAttr("root_cc.Show_Helmet", "helmet_cc_grp.v")

    # hangingStrap
    self.make_FkChain(joints=["groinStrap1", "groinStrap2"], module_name="GroinStrap", side="c", control_shape="Cube")
    # zipper
    self.make_SingleJoint(joint="zipper", module_name="Zipper", side="RT", control_shape="Cube", child_of="pelvis_cc", constrained_to="RT_upLegTwist_03")
    # gloveChord
    self.make_SingleJoint(joint="LF_gloveChord", module_name="GloveChord", side="LF", control_shape="Cube", child_of="LF_clavicle_cc", constrained_to="LF_loArmTwist_01")
    cmds.parentConstraint("LF_wrist_drive", "LF_loArmTwist_01", "LF_gloveChord_cc_grp", maintainOffset=True)
    # radio
    self.make_SingleJoint(joint="radio", module_name="Radio", side=None, control_shape="Cube")
    # tank
    self.make_SingleJoint(joint="tank", module_name="Tank", side=None, control_shape="Cylinder")
    # tankTubes
    self.make_SingleJoint(joint="LF_tankTube01", module_name="LF_tankTube01", side="LF", control_shape="Cube")
    cmds.parentConstraint("tank_cc", "chest_cc", "LF_tankTube01_cc_grp", mo=1)
    self.make_SingleJoint(joint="LF_tankTube02", module_name="LF_tankTube02", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="LF_tankTube03", module_name="LF_tankTube03", side="LF", control_shape="Cube")

    self.make_SingleJoint(joint="RT_tankTube01", module_name="RT_tankTube01", side="RT", control_shape="Cube")
    cmds.parentConstraint("tank_cc", "chest_cc", "RT_tankTube01_cc_grp", mo=1)
    self.make_SingleJoint(joint="RT_tankTube02", module_name="RT_tankTube02", side="RT", control_shape="Cube")
    self.make_SingleJoint(joint="RT_tankTube03", module_name="RT_tankTube03", side="RT", control_shape="Cube")

    cable_joints = ["toolCable_01", "toolCable_02", "toolCable_03", "toolCable_04", "toolCable_05", "toolCable_06", "toolCable_07", "toolCable_08", "toolCable_09", "toolCable_10", "toolCable_11", "toolCable_12", "toolCable_13", "toolCable_14", "toolCable_15", "toolCable_16", "toolCable_17", "toolCable_18", "toolCable_19"]
    # cable_joints = ["toolCable_01", "toolCable_02", "toolCable_03", "toolCable_04", "toolCable_05", "toolCable_06"]

    # tool tube
    self.make_SplineIK(module_name="Cable", side=None, joints=cable_joints, stretchy=True, num_controls=5)

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Ygark_grp")
    cmds.parent("exclude", "rig")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.hide("exclude")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sy", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sz", l=1, cb=0, k=0)

    cmds.select(cl=1)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

