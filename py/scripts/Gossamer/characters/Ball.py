import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Ball(Gossamer.creator.Creator):
  """Character creator class for the Ball rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Ball"):
    super(Ball, self).__init__(char_name=char_name)
    
  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="cog_secondary", module_name="cog_secondary", side="c", control_shape="Circle")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    # ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Ball_grp")

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

