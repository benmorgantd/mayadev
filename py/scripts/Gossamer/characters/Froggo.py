import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Froggo(Gossamer.creator.Creator):
  """Character creator class for the Froggo rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Froggo"):
    super(Froggo, self).__init__(char_name=char_name)
    
  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    self.make_SingleJoint(joint="hips", module_name="Hips", side="c", control_shape="Cube")

    # Spine
    self.make_FkChain(joints=["spine1", "spine2", "chest"], module_name="Spine", side="c")

    # Neck and Head
    self.make_SingleJoint(joint="neck", module_name="Neck", side="c", control_shape="Cylinder")
    head = self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")
    head.setup_world_follow(control="head_cc", constraint_type="orient", defaultValue=1, module=head.node)

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")
    
    # feet
    self.make_SingleJoint(joint="LF_toe", module_name="LF_toe", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_toe", module_name="RT_toe", side="RT", control_shape="Cube")

    # #hips 
    # lf_upLeg = self.make_SingleJoint(joint="LF_upLeg", module_name="LF_upLeg", side="LF", control_shape="Cylinder")
    # rt_upLeg = self.make_SingleJoint(joint="RT_upLeg", module_name="RT_upLeg", side="RT", control_shape="Cylinder")

    # # upper legs
    # LF_upLeg = self.make_IkFkLeg(joints=["LF_loLeg", "LF_ankle", "LF_foot"], module_name="LF_Leg", side="LF")
    # RT_upLeg = self.make_IkFkLeg(joints=["RT_loLeg", "RT_ankle", "RT_foot"], module_name="RT_Leg", side="RT")


    # # Feet
    # self.make_Foot(joints=["LF_foot", "LF_toe", "LF_toeTip"], locs=["LF_heel", "LF_bankIn_loc", "LF_bankOut_loc"], module_name="LF_Foot", side="LF")
    # self.make_Foot(joints=["RT_foot", "RT_toe", "RT_toeTip"], locs=["RT_heel", "RT_bankIn_loc", "RT_bankOut_loc"], module_name="RT_Foot", side="RT")

    # # (Fix for foot module fk visibility switching)
    # cmds.connectAttr("LF_leg_ikSwitch_cc.ikFk", "LF_toe_fk_ccShape.v")
    # cmds.connectAttr("RT_leg_ikSwitch_cc.ikFk", "RT_toe_fk_ccShape.v")

    # toes
    self.make_SingleJoint(joint="LF_toeIn", module_name="LF_toeIn", side="LF", control_shape="Cube", child_of="hips_cc", constrained_to="LF_toe")
    self.make_SingleJoint(joint="LF_toeMid", module_name="LF_toeMid", side="LF", control_shape="Cube", child_of="hips_cc", constrained_to="LF_toe")
    self.make_SingleJoint(joint="LF_toeOut", module_name="LF_toeOut", side="LF", control_shape="Cube", child_of="hips_cc", constrained_to="LF_toe")

    self.make_SingleJoint(joint="RT_toeIn", module_name="RT_toeIn", side="RT", control_shape="Cube", child_of="hips_cc", constrained_to="RT_toe")
    self.make_SingleJoint(joint="RT_toeMid", module_name="RT_toeMid", side="RT", control_shape="Cube", child_of="hips_cc", constrained_to="RT_toe")
    self.make_SingleJoint(joint="RT_toeOut", module_name="RT_toeOut", side="RT", control_shape="Cube", child_of="hips_cc", constrained_to="RT_toe")

    # Arms
    LF_arm = self.make_IkFkArm(joints=["LF_upArm", "LF_loArm", "LF_wrist"], module_name="LF_Arm", side="LF")
    RT_arm = self.make_IkFkArm(joints=["RT_upArm", "RT_loArm", "RT_wrist"], module_name="RT_Arm", side="RT")
    
    # Twist extraction via Quat and scIK extraction depending on where it works better.
    self.make_QuatTwist(module_name="LF_loArm_twist", side="LF", extract_joint="LF_wrist_drive", twist_joints=["LF_loArmTwist_01", "LF_loArmTwist_02"])
    self.make_QuatTwist(module_name="RT_loArm_twist", side="RT", extract_joint="RT_wrist_drive", twist_joints=["RT_loArmTwist_01", "RT_loArmTwist_02"])
    
    self.make_IkTwist(module_name="LF_upArm_twist", side="LF", extract_joint="LF_upArm_drive", start_joint="LF_loArm_drive", twist_joints=["LF_upArmTwist_03", "LF_upArmTwist_02", "LF_upArmTwist_01"], ik_parent="LF_clavicle")
    self.make_IkTwist(module_name="RT_upArm_twist", side="RT", extract_joint="RT_upArm_drive", start_joint="RT_loArm_drive", twist_joints=["RT_upArmTwist_03", "RT_upArmTwist_02", "RT_upArmTwist_01"], ik_parent="RT_clavicle")

    self.make_SingleJoint(joint="belly", side="c", module_name="Belly", control_shape="Circle")
    self.make_SingleJoint(joint="jaw", side="c", module_name="Jaw", control_shape="Cylinder")

    self.make_SingleJoint(joint="LF_cheek", side="LF", module_name="LF_cheek", control_shape="Sphere")
    self.make_SingleJoint(joint="RT_cheek", side="RT", module_name="RT_cheek", control_shape="Sphere")
    cmds.scaleConstraint("LF_cheek_cc", "LF_cheek")
    cmds.scaleConstraint("RT_cheek_cc", "RT_cheek")

    self.make_SingleJoint(joint="LF_eye", side="LF", module_name="LF_eye", control_shape="Sphere")
    self.make_SingleJoint(joint="RT_eye", side="RT", module_name="RT_eye", control_shape="Sphere")

    # tongue
    self.make_SplineIK(joints=["tongue_1", "tongue_2","tongue_3","tongue_4","tongue_5"], module_name="Tongue", side="c", stretchy=True, num_controls=3, control_shape="Cube")

    # Fingers
    self.make_FkChain(module_name="LF_index", side="LF", joints=["LF_index1","LF_index2"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_mid", side="LF", joints=["LF_mid1","LF_mid2"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_pinkie", side="LF", joints=["LF_pinkie1","LF_pinkie2","LF_pinkie3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_thumb", side="LF", joints=["LF_thumb1","LF_thumb2"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")

    self.make_FkChain(module_name="RT_index", side="RT", joints=["RT_index1","RT_index2"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_mid", side="RT", joints=["RT_mid1","RT_mid2"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_pinkie", side="RT", joints=["RT_pinkie1","RT_pinkie2","RT_pinkie3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_thumb", side="RT", joints=["RT_thumb1","RT_thumb2"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")

    tongue_grp = cmds.group("Tongue_1_grp", "Tongue_2_grp", "Tongue_3_grp", name="Tongue_rig", parent="jaw_cc")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Froggo_grp")
    cmds.parent("exclude", "rig")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      if "cheek" not in obj:
        cmds.setAttr(obj + ".sx", lock=True, keyable=False, cb=0)
        cmds.setAttr(obj + ".sy", lock=True, keyable=False, channelBox=False)
        cmds.setAttr(obj + ".sz", lock=True, keyable=False, channelBox=False)

    cmds.select(cl=1)

    import Gossamer.modules.dogLeg_rough as dogLeg_rough
    reload(dogLeg_rough)

    dogLeg_rough.DogLeg(upLeg="LF_upLeg",loLeg="LF_loLeg",ankle="LF_ankle",toe="LF_foot",toeEnd="LF_toe", side="LF")

    dogLeg_rough.DogLeg(upLeg="RT_upLeg",loLeg="RT_loLeg",ankle="RT_ankle",toe="RT_foot",toeEnd="RT_toe", side="RT")


    cmds.parent("LF_toe_cc_grp", "LF_leg_cc")
    cmds.parent("RT_toe_cc_grp", "RT_leg_cc")

    cmds.parent("LF_leg_grp", "RT_leg_grp", "LF_leg_pv_grp", "RT_leg_pv_grp", "layout_cc")


    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

