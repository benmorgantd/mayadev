import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class SonyBendTest(Gossamer.creator.Creator):
  """Character creator class for the SonyBendTest rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="SonyBendTest"):
    super(SonyBendTest, self).__init__(char_name=char_name)

  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("Hips", "layout")
    self.make_SingleJoint(joint="Hips", module_name="Hips", side="c", control_shape="4-Sided Arrow")

    # Spine
    self.make_FkChain(joints=["cog", "spine", "spine1","spine2","spine3","spine4"], module_name="Spine", side="c")

    # Neck and Head
    self.make_SingleJoint(joint="Neck", module_name="Neck", side="c", control_shape="Cylinder")
    # self.make_SingleJoint(joint="Head", module_name="Head", side="c", control_shape="Sphere", child_of="Neck_cc")

    # Clavicles
    self.make_SingleJoint(joint="LeftShoulder", module_name="LeftShoulder", side="Left", control_shape="Circle")
    self.make_SingleJoint(joint="RightShoulder", module_name="RightShoulder", side="Right", control_shape="Circle")

    # Arms
    Left_arm = self.make_IkFkArm(joints=["LeftArm", "LeftForeArm", "LeftHand"], module_name="Left_Arm", side="Left")
    Right_arm = self.make_IkFkArm(joints=["RightArm", "RightForeArm", "RightHand"], module_name="Right_Arm", side="Right")

    # Twist extraction via Quat and scIK extraction depending on where it works better.
    self.make_QuatTwist(module_name="Left_loArm_twist", side="Left", extract_joint="LeftHand", 
                        twist_joints=["LeftLoArmTwist_03", "LeftLoArmTwist_02", "LeftLoArmTwist_01"], 
                        limb_module=Left_arm.node)

    self.make_QuatTwist(module_name="Right_loArm_twist", side="Right", extract_joint="RightHand",
                        twist_joints=["RightLoArmTwist_03", "RightLoArmTwist_02", "RightLoArmTwist_01"],
                        limb_module=Right_arm.node)
    
    # self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="Head", twist_joints=["Neck1"], multiplier=.5)
    
    self.make_IkTwist(module_name="Left_upArm_twist", side="Left", extract_joint="LeftArm_drive", start_joint="LeftForeArm_drive", twist_joints=["LeftUpArmTwist_01", "LeftUpArmTwist_02", "LeftUpArmTwist_03"], ik_parent="LeftShoulder")
    self.make_IkTwist(module_name="Right_upArm_twist", side="Right", extract_joint="RightArm_drive", start_joint="RightForeArm_drive", twist_joints=["RightUpArmTwist_01", "RightUpArmTwist_02", "RightUpArmTwist_03"], ik_parent="RightShoulder")

    # Fingers
    self.make_Finger(module_name="Left_index", side="Left", joints=["LeftHandIndex","LeftHandIndex1","LeftHandIndex2","LeftHandIndex3"], child_of="LeftShoulder_cc", constrained_to="LeftHand_drive")
    self.make_Finger(module_name="Left_mid", side="Left", joints=["LeftHandMiddle","LeftHandMiddle1","LeftHandMiddle2","LeftHandMiddle3"], child_of="LeftShoulder_cc", constrained_to="LeftHand_drive")
    self.make_Finger(module_name="Left_ring", side="Left", joints=["LeftHandRing","LeftHandRing1","LeftHandRing2","LeftHandRing3"], child_of="LeftShoulder_cc", constrained_to="LeftHand_drive")
    self.make_Finger(module_name="Left_pinkie", side="Left", joints=["LeftInHandPinky","LeftInHandPinky1","LeftInHandPinky2","LeftInHandPinky3"], child_of="LeftShoulder_cc", constrained_to="LeftHand_drive")
    self.make_Finger(module_name="Left_thumb", side="Left", joints=["LeftHandThumb1","LeftHandThumb2","LeftHandThumb3"], child_of="LeftShoulder_cc", constrained_to="LeftHand_drive")

    self.make_Finger(module_name="Right_index", side="Right", joints=["RightHandIndex","RightHandIndex1","RightHandIndex2","RightHandIndex3"], child_of="RightShoulder_cc", constrained_to="RightHand_drive")
    self.make_Finger(module_name="Right_mid", side="Right", joints=["RightHandMiddle","RightHandMiddle1","RightHandMiddle2","RightHandMiddle3"], child_of="RightShoulder_cc", constrained_to="RightHand_drive")
    self.make_Finger(module_name="Right_ring", side="Right", joints=["RightHandRing","RightHandRing1","RightHandRing2","RightHandRing3"], child_of="RightShoulder_cc", constrained_to="RightHand_drive")
    self.make_Finger(module_name="Right_pinkie", side="Right", joints=["RightInHandPinky","RightInHandPinky1","RightInHandPinky2","RightInHandPinky3"], child_of="RightShoulder_cc", constrained_to="RightHand_drive")
    self.make_Finger(module_name="Right_thumb", side="Right", joints=["RightHandThumb1","RightHandThumb2","RightHandThumb3"], child_of="RightShoulder_cc", constrained_to="RightHand_drive")


    
    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    try:
        ctrl_cv_data.set_cv_data(self.char_name)
    except KeyError:
        pass
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "SonyBendTest_grp")
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

