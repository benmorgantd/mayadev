import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Vance(Gossamer.creator.Creator):
  """Character creator class for the Vance rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Vance"):
    super(Vance, self).__init__(char_name=char_name)

  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG
    cmds.parent("chest", "layout")

    # Chest, Neck and Head
    self.make_SingleJoint(joint="chest", module_name="Chest", side="c", control_shape="Cube")
    self.make_SingleJoint(joint="neck", module_name="Neck", side="c", control_shape="Cylinder")
    self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="upHead", module_name="upHead", side="c", control_shape="Circle")
    self.make_SingleJoint(joint="jaw", module_name="jaw", side="c", control_shape="Cylinder")
    self.make_SingleJoint(joint="tongue", module_name="tongue", side="c", control_shape="Circle")

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")

    self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="head", twist_joints=["neckTwist_01"], multiplier=.5)
    
    # face
    self.make_SingleJoint(module_name = "Nose", side="c", joint="nose", control_shape="Cube")
    self.make_SingleJoint(module_name = "LF_nostril", side="LF", joint="LF_nostril", control_shape="Cube")
    self.make_SingleJoint(module_name = "RT_nostril", side="RT", joint="RT_nostril", control_shape="Cube")

    self.make_SingleJoint(module_name="upLipMid", joint="upLipMid", side="c", control_shape="Cube")
    self.make_SingleJoint(module_name="loLipMid", joint="loLipMid", side="c", control_shape="Cube")
    self.make_SingleJoint(module_name="chin", joint="chin", side="c", control_shape="Cube")
    self.make_SingleJoint(module_name="browMid", joint="browMid", side="c", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_loCheek01", joint="LF_loCheek01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_loCheek02", joint="LF_loCheek02", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_midCheek01", joint="LF_midCheek01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_midCheek02", joint="LF_midCheek02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_midCheek03", joint="LF_midCheek03", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_upCheek01", joint="LF_upCheek01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upCheek02", joint="LF_upCheek02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upCheek03", joint="LF_upCheek03", side="LF", control_shape="Cube")
    
    self.make_SingleJoint(module_name="LF_nasolabial", joint="LF_nasolabial", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_lidCorner_in", joint="LF_lidCorner_in", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_lidCorner_out", joint="LF_lidCorner_out", side="LF", control_shape="Cube")
    
    self.make_SingleJoint(module_name="LF_upLid01", joint="LF_upLid01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upLid02", joint="LF_upLid02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upLid03", joint="LF_upLid03", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_loLid01", joint="LF_loLid01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_loLid02", joint="LF_loLid02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_loLid03", joint="LF_loLid03", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_brow01", joint="LF_brow01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_brow02", joint="LF_brow02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_brow03", joint="LF_brow03", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_browbone01", joint="LF_browbone01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_browbone02", joint="LF_browbone02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_browbone03", joint="LF_browbone03", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_upLip01", joint="LF_upLip01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upLip02", joint="LF_upLip02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upLip03", joint="LF_upLip03", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_loLip01", joint="LF_loLip01", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_loLip02", joint="LF_loLip02", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_loLip03", joint="LF_loLip03", side="LF", control_shape="Cube")
    
    self.make_SingleJoint(module_name="LF_ear", joint="LF_ear", side="LF", control_shape="Cube")

    # RIGHT

    self.make_SingleJoint(module_name="RT_loCheek01", joint="RT_loCheek01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_loCheek02", joint="RT_loCheek02", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_midCheek01", joint="RT_midCheek01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_midCheek02", joint="RT_midCheek02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_midCheek03", joint="RT_midCheek03", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_upCheek01", joint="RT_upCheek01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upCheek02", joint="RT_upCheek02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upCheek03", joint="RT_upCheek03", side="RT", control_shape="Cube")
    
    self.make_SingleJoint(module_name="RT_nasolabial", joint="RT_nasolabial", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_lidCorner_in", joint="RT_lidCorner_in", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_lidCorner_out", joint="RT_lidCorner_out", side="RT", control_shape="Cube")
    
    self.make_SingleJoint(module_name="RT_upLid01", joint="RT_upLid01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upLid02", joint="RT_upLid02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upLid03", joint="RT_upLid03", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_loLid01", joint="RT_loLid01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_loLid02", joint="RT_loLid02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_loLid03", joint="RT_loLid03", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_brow01", joint="RT_brow01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_brow02", joint="RT_brow02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_brow03", joint="RT_brow03", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_browbone01", joint="RT_browbone01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_browbone02", joint="RT_browbone02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_browbone03", joint="RT_browbone03", side="RT", control_shape="Cube")


    self.make_SingleJoint(module_name="RT_upLip01", joint="RT_upLip01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upLip02", joint="RT_upLip02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upLip03", joint="RT_upLip03", side="RT", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_loLip01", joint="RT_loLip01", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_loLip02", joint="RT_loLip02", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_loLip03", joint="RT_loLip03", side="RT", control_shape="Cube")
    
    self.make_SingleJoint(module_name="RT_ear", joint="RT_ear", side="RT", control_shape="Cube")

    
    # setup extra facial controls
    cmds.parent("upLip_cc_grp", "head_cc")
    cmds.parent("LF_brow_cc_grp", "RT_brow_cc_grp","LF_upLid_cc_grp" , "RT_upLid_cc_grp", "LF_loLid_cc_grp", "RT_loLid_cc_grp","upHead_cc")
    cmds.parent("loLip_cc_grp", "jaw_cc")

    cmds.parent("LF_upLid01_cc_grp","LF_upLid02_cc_grp","LF_upLid03_cc_grp", "LF_upLid_cc")
    cmds.parent("RT_upLid01_cc_grp","RT_upLid02_cc_grp","RT_upLid03_cc_grp", "RT_upLid_cc")

    cmds.parent("LF_loLid01_cc_grp","LF_loLid02_cc_grp","LF_loLid03_cc_grp", "LF_loLid_cc")
    cmds.parent("RT_loLid01_cc_grp","RT_loLid02_cc_grp","RT_loLid03_cc_grp", "RT_loLid_cc")

    cmds.parent("LF_brow01_cc_grp", "LF_brow02_cc_grp", "LF_brow03_cc_grp", "LF_brow_cc")
    cmds.parent("RT_brow01_cc_grp", "RT_brow02_cc_grp", "RT_brow03_cc_grp", "RT_brow_cc")

    cmds.parent("LF_upLip01_cc_grp", "LF_upLip02_cc_grp",
                "RT_upLip01_cc_grp", "RT_upLip02_cc_grp", 
                "upLipMid_cc_grp", "upLip_cc")

    cmds.parent("LF_loLip01_cc_grp", "LF_loLip02_cc_grp",
                "RT_loLip01_cc_grp", "RT_loLip02_cc_grp",
                "loLipMid_cc_grp", "loLip_cc")

    cmds.aimConstraint("LF_eyeAim_cc", "LF_eye", mo=1, aimVector=(0,0,1), upVector=(0,1,0))
    cmds.aimConstraint("RT_eyeAim_cc", "RT_eye", mo=1, aimVector=(0,0,-1), upVector=(0,1,0))

    cmds.parent("eyes_grp", "head_cc")
    const = cmds.parentConstraint("worldSpace", "eyes_space", mo=1)
    cmds.connectAttr("eyes_cc.Follow", const[0] + ".worldSpaceW0")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Vance_grp")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl", noRecurse=True)

    scale_exclude = ["head_cc", "upHead_cc", "jaw_cc", "nose_cc",
                    "upLip_cc", "loLip_cc", "LF_brow_cc", "RT_brow_cc",
                    "LF_upLid_cc", "LF_loLid_cc", "RT_upLid_cc", "Rt_loLid_cc"]

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      if cmds.listRelatives(cmds.listRelatives(obj, parent=True)[0], parent=True)[0] not in scale_exclude:
        cmds.setAttr(obj + ".sx", l=1, cb=0, k=0)
        cmds.setAttr(obj + ".sy", l=1, cb=0, k=0)
        cmds.setAttr(obj + ".sz", l=1, cb=0, k=0)

    cmds.select(cl=1)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

