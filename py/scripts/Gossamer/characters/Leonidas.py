import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Leonidas(Gossamer.creator.Creator):
  """Character creator class for the Leonidas rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Leonidas"):
    super(Leonidas, self).__init__(char_name=char_name)

  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    self.make_SingleJoint(joint="lumbar", module_name="lumbar", side="c", control_shape="Cube")
    self.make_SingleJoint(joint="pelvis", module_name="Pelvis", side="c", control_shape="Cube")

    self.make_FkChain(joints=["spine01", "spine02", "spine03", "spine04", "spine05"], module_name="Spine", side="c")

    self.make_FkChain(joints=["LF_tail01", "LF_tail02", "LF_tail03", "LF_tail04", "LF_tail05", "LF_tail06", "LF_tail07", "LF_tail08", "LF_tail09"], module_name="LF_tail", side="LF")
    self.make_FkChain(joints=["RT_tail01", "RT_tail02", "RT_tail03", "RT_tail04", "RT_tail05", "RT_tail06", "RT_tail07", "RT_tail08", "RT_tail09"], module_name="RT_tail", side="RT")

    self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="LF_eye", module_name="LF_eye", side="LF", control_shape="Sphere")
    self.make_SingleJoint(joint="RT_eye", module_name="RT_eye", side="RT", control_shape="Sphere")

    self.make_FkChain(joints=["LF_ear01","LF_ear02","LF_ear03"], module_name="LF_ear", side="LF")
    self.make_FkChain(joints=["RT_ear01","RT_ear02","RT_ear03"], module_name="RT_ear", side="RT")

    # Clavicles
    self.make_SingleJoint(joint="LF_scapula", module_name="LF_scapula", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_scapula", module_name="RT_scapula", side="RT", control_shape="Circle")

    LF_arm = self.make_IkFkArm(joints=["LF_upArm", "LF_loArm", "LF_wrist"], module_name="LF_Arm", side="LF")
    RT_arm = self.make_IkFkArm(joints=["RT_upArm", "RT_loArm", "RT_wrist"], module_name="RT_Arm", side="RT")

    # self.make_SingleJoint(joint="LF_metacarpals", side="LF", module_name="LF_metacarpals", control_shape="Cube")
    # self.make_SingleJoint(joint="RT_metacarpals", side="RT", module_name="RT_metacarpals", control_shape="Cube")
    
    self.make_SingleJoint(joint="LF_finger01", side="LF", module_name="LF_finger01", control_shape="Cube")
    self.make_SingleJoint(joint="LF_finger02", side="LF", module_name="LF_finger02", control_shape="Cube")
    self.make_SingleJoint(joint="LF_finger03", side="LF", module_name="LF_finger03", control_shape="Cube")
    self.make_SingleJoint(joint="LF_finger04", side="LF", module_name="LF_finger04", control_shape="Cube")

    self.make_SingleJoint(joint="RT_finger01", side="RT", module_name="RT_finger01", control_shape="Cube")
    self.make_SingleJoint(joint="RT_finger02", side="RT", module_name="RT_finger02", control_shape="Cube")
    self.make_SingleJoint(joint="RT_finger03", side="RT", module_name="RT_finger03", control_shape="Cube")
    self.make_SingleJoint(joint="RT_finger04", side="RT", module_name="RT_finger04", control_shape="Cube")

    self.make_SingleJoint(joint="LF_toe01", side="LF", module_name="LF_toe01", control_shape="Cube")
    self.make_SingleJoint(joint="LF_toe02", side="LF", module_name="LF_toe02", control_shape="Cube")
    self.make_SingleJoint(joint="LF_toe03", side="LF", module_name="LF_toe03", control_shape="Cube")
    self.make_SingleJoint(joint="LF_toe04", side="LF", module_name="LF_toe04", control_shape="Cube")

    self.make_SingleJoint(joint="RT_toe01", side="RT", module_name="RT_toe01", control_shape="Cube")
    self.make_SingleJoint(joint="RT_toe02", side="RT", module_name="RT_toe02", control_shape="Cube")
    self.make_SingleJoint(joint="RT_toe03", side="RT", module_name="RT_toe03", control_shape="Cube")
    self.make_SingleJoint(joint="RT_toe04", side="RT", module_name="RT_toe04", control_shape="Cube")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Leonidas_grp")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("rig", name="ctrl", noRecurse=True)

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sy", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sz", l=1, cb=0, k=0)

    cmds.select(cl=1)

    om.MGlobal.displayInfo(self.char_name + " rigged in %.3f seconds! :D"%(time.time() - start_time))

