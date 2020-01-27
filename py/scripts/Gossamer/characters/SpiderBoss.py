import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class SpiderBoss(Gossamer.creator.Creator):
  """Character creator class for the SpiderBoss rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="SpiderBoss"):
    cmds.file(r"D:/Documents/Google Drive/Jobs/Mothbitch/spider boss/spiderBoss_riggingReady_05.ma", open=True, force=True)

    super(SpiderBoss, self).__init__(char_name=char_name)
    
  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    abdomin = self.make_SingleJoint(joint="abdomin", module_name="abdomin", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="cogwheel", module_name="cogwheel", side="c", control_shape="Cylinder")

    # Neck and Head
    head = self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")

    self.make_SingleJoint(joint="LF_eye", module_name="LF_eye", side="LF", control_shape="Sphere")
    self.make_SingleJoint(joint="RT_eye", module_name="RT_eye", side="RT", control_shape="Sphere")

    self.make_SingleJoint(joint="LF_fang", module_name="LF_fang", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_fang", module_name="RT_fang", side="RT", control_shape="Cube")

    # Legs
    self.make_IkChain(startJoint="LF_leg1_01", endJoint="LF_leg1_04", side="LF", joints=["LF_leg1_0{0}".format(i) for i in range(1, 5)], module_name="LF_leg1", control_shape="Cube")
    self.make_IkChain(startJoint="LF_leg2_01", endJoint="LF_leg2_04", side="LF", module_name="LF_leg2", joints=["LF_leg2_0{0}".format(i) for i in range(1, 5)], control_shape="Cube")
    self.make_IkChain(startJoint="LF_leg3_01", endJoint="LF_leg3_05", side="LF", module_name="LF_leg3", joints=["LF_leg3_0{0}".format(i) for i in range(1, 6)], control_shape="Cube")
    self.make_IkChain(startJoint="LF_leg4_01", endJoint="LF_leg4_05", side="LF", module_name="LF_leg4", joints=["LF_leg4_0{0}".format(i) for i in range(1, 6)],control_shape="Cube")

    for i in range(1, 5):
        self.make_ScIk(joint="LF_leg{0}_piston01".format(i), module_name="LF_leg{0}_piston".format(i), side="LF", control_shape="Cube", child_of="layout_cc", constrained_to="cog_cc", down_vector=cmds.xform("LF_leg{0}_piston02".format(i), q=1, t=1))
        cmds.parentConstraint("LF_leg{0}_02".format(i), "LF_leg{0}_piston01_ik_cc_grp".format(i), mo=1)

        cmds.parentConstraint("LF_leg{0}_piston01_ik_cc".format(i), "LF_leg{0}_piston02".format(i), mo=1)

    self.make_IkChain(startJoint="RT_leg1_01", endJoint="RT_leg1_04", side="RT", joints=["RT_leg1_0{0}".format(i) for i in range(1, 5)], module_name="RT_leg1", control_shape="Cube")
    self.make_IkChain(startJoint="RT_leg2_01", endJoint="RT_leg2_04", side="RT", module_name="RT_leg2", joints=["RT_leg2_0{0}".format(i) for i in range(1, 5)], control_shape="Cube")
    self.make_IkChain(startJoint="RT_leg3_01", endJoint="RT_leg3_05", side="RT", module_name="RT_leg3", joints=["RT_leg3_0{0}".format(i) for i in range(1, 6)], control_shape="Cube")
    self.make_IkChain(startJoint="RT_leg4_01", endJoint="RT_leg4_05", side="RT", module_name="RT_leg4", joints=["RT_leg4_0{0}".format(i) for i in range(1, 6)],control_shape="Cube")

    for i in range(1, 5):
        self.make_ScIk(joint="RT_leg{0}_piston01".format(i), module_name="RT_leg{0}_piston".format(i), side="RT", control_shape="Cube", child_of="layout_cc", constrained_to="cog_cc", down_vector=cmds.xform("RT_leg{0}_piston02".format(i), q=1, t=1))
        cmds.parentConstraint("RT_leg{0}_02".format(i), "RT_leg{0}_piston01_ik_cc_grp".format(i), mo=1)
       
        cmds.parentConstraint("RT_leg{0}_piston01_ik_cc".format(i), "RT_leg{0}_piston02".format(i), mo=1)

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "SpiderBoss_grp")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1, k=0)
      cmds.setAttr(obj + ".sy", l=1, k=0)
      cmds.setAttr(obj + ".sz", l=1, k=0)
      cmds.setAttr(obj + ".v", l=1, k=0)

    cmds.select(cl=1)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

SpiderBoss()