import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Corgo(Gossamer.creator.Creator):
  """Character creator class for the Corgo rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Corgo"):
    super(Corgo, self).__init__(char_name=char_name)
    
  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    self.make_SingleJoint(joint="hips", module_name="Hips", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="tail", module_name="Tail", side="c", control_shape="Cube")

    self.make_SingleJoint(joint="scroll", module_name="Scroll", side=None, control_shape="Cylinder")
    self.make_FkChain(joints=["feather_01", "feather_02"], module_name="Feather", side=None, control_shape="Cube")

    self.make_SingleJoint(joint="LF_pack", module_name="Scroll", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_pack", module_name="Scroll", side="RT", control_shape="Cube")

    # Neck and Head
    self.make_SingleJoint(joint="chest", module_name="Chest", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="LF_lid", module_name="LF_lid", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_lid", module_name="RT_lid", side="RT", control_shape="Cube")

    self.make_SingleJoint(joint="LF_brow", module_name="LF_brow", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_brow", module_name="RT_brow", side="RT", control_shape="Cube")

    self.make_SingleJoint(joint="LF_ear", module_name="LF_ear", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_ear", module_name="RT_ear", side="RT", control_shape="Cube")

    self.make_SingleJoint(joint="nose", module_name="Nose", side="c", control_shape="Sphere")
    self.make_FkChain(joints=["jaw", "tongue"], module_name="Jaw", side="c", control_shape="Cube")

    # Clavicles
    self.make_SingleJoint(joint="LF_scapula", module_name="LF_scapula", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_scapula", module_name="RT_scapula", side="RT", control_shape="Circle")

    self.make_SingleJoint(joint="LF_bellyShield", module_name="LF_bellyShield", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_bellyShield", module_name="RT_bellyShield", side="RT", control_shape="Cube")
    
    self.make_SingleJoint(joint="frontArmor", module_name="frontArmor", side="c", control_shape="Circle")

    # Front Leg
    self.make_IkFkLeg(joints=["LF_upFrontLeg", "LF_loFrontLeg", "LF_frontPaw"], module_name="LF_frontLeg", side="LF_front_")
    self.make_IkFkLeg(joints=["RT_upFrontLeg", "RT_loFrontLeg", "RT_frontPaw"], module_name="RT_frontLeg", side="RT_front_")

    # Rear Leg
    self.make_IkFkLeg(joints=["LF_upRearLeg", "LF_loRearLeg", "LF_rearPaw"], module_name="LF_rearLeg", side="LF_rear_")
    self.make_IkFkLeg(joints=["RT_upRearLeg", "RT_loRearLeg", "RT_rearPaw"], module_name="RT_rearLeg", side="RT_rear_")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Corgo_grp")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1)
      cmds.setAttr(obj + ".sy", l=1)
      cmds.setAttr(obj + ".sz", l=1)

    cmds.select(cl=1)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

