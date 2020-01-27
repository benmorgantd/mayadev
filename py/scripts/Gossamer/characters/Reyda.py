import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
reload(character)
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import Gossamer.library.wtAddMatrix_face as face
reload(face)

import time
import maya.OpenMaya as om
import maya.cmds as cmds
import shutil
import os


class Reyda(Gossamer.creator.Creator):
  """Character creator class for the Reyda rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def _init_(self, char_name="Reyda"):
    super(Reyda, self)._init_(char_name=char_name)

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
    self.make_FkChain(joints=["spine_01", "chest"], module_name="Spine", side="c")

    # Neck and Head
    self.make_SingleJoint(joint="neck", module_name="Neck", side="c", control_shape="Cylinder")
    head = self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")
    head.setup_world_follow(control="head_cc", constraint_type="orient", defaultValue=0, module=head.node)

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")

    self.make_SingleJoint(joint="LF_collar", module_name="LF_collar", side="LF", child_of="neck_cc", constrained_to="neckTwist_01", control_shape="Cube")
    self.make_SingleJoint(joint="RT_collar", module_name="RT_collar", side="RT", child_of="neck_cc", constrained_to="neckTwist_01", control_shape="Cube")

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
                        twist_joints=["LF_loArmTwist_01", "LF_loArmTwist_02", "LF_loArmTwist_03"], 
                        limb_module=LF_arm.node)

    self.make_QuatTwist(module_name="RT_loArm_twist", side="RT", extract_joint="RT_wrist_drive",
                        twist_joints=["RT_loArmTwist_01", "RT_loArmTwist_02", "RT_loArmTwist_03"],
                        limb_module=RT_arm.node)
    
    self.make_QuatTwist(module_name="LF_loLeg_twist", side="LF", extract_joint="LF_foot_drive", twist_joints=["LF_loLegTwist_01", "LF_loLegTwist_02", "LF_loLegTwist_03"], axis="Y", multiplier=-1)
    self.make_QuatTwist(module_name="RT_loLeg_twist", side="RT", extract_joint="RT_foot_drive", twist_joints=["RT_loLegTwist_01", "RT_loLegTwist_02", "RT_loLegTwist_03"], axis="Y")

    self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="head", twist_joints=["neckTwist_01"], multiplier=.5)
    
    self.make_IkTwist(module_name="LF_upLeg_twist", side="LF", extract_joint="LF_upLeg_drive", start_joint="LF_loLeg_drive", twist_joints=["LF_upLegTwist_01", "LF_upLegTwist_02", "LF_upLegTwist_03"], ik_parent="pelvis")
    self.make_IkTwist(module_name="RT_upLeg_twist", side="RT", extract_joint="RT_upLeg_drive",  start_joint="RT_loLeg_drive",twist_joints=["RT_upLegTwist_01", "RT_upLegTwist_02", "RT_upLegTwist_03"], ik_parent="pelvis")

    self.make_IkTwist(module_name="LF_upArm_twist", side="LF", extract_joint="LF_upArm_drive", start_joint="LF_loArm_drive", twist_joints=["LF_upArmTwist_01", "LF_upArmTwist_02", "LF_upArmTwist_03"], ik_parent="LF_clavicle")
    self.make_IkTwist(module_name="RT_upArm_twist", side="RT", extract_joint="RT_upArm_drive", start_joint="RT_loArm_drive", twist_joints=["RT_upArmTwist_01", "RT_upArmTwist_02", "RT_upArmTwist_03"], ik_parent="RT_clavicle")

    # Fingers
    self.make_Finger(module_name="LF_index", side="LF", joints=["LF_index_01","LF_index_02","LF_index_03","LF_index_04"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_Finger(module_name="LF_mid", side="LF", joints=["LF_mid_01","LF_mid_02","LF_mid_03","LF_mid_04"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_SingleJoint(module_name="LF_handCup", side="LF", joint="LF_handCup", control_shape="Cylinder", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_Finger(module_name="LF_ring", side="LF", joints=["LF_ring_01","LF_ring_02","LF_ring_03","LF_ring_04"], child_of="LF_clavicle_cc", constrained_to="LF_handCup")
    self.make_Finger(module_name="LF_pinkie", side="LF", joints=["LF_pinkie_01","LF_pinkie_02","LF_pinkie_03","LF_pinkie_04"], child_of="LF_clavicle_cc", constrained_to="LF_handCup")
    self.make_Finger(module_name="LF_thumb", side="LF", joints=["LF_thumb_01","LF_thumb_02","LF_thumb_03"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")

    self.make_Finger(module_name="RT_index", side="RT", joints=["RT_index_01","RT_index_02","RT_index_03","RT_index_04"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_Finger(module_name="RT_mid", side="RT", joints=["RT_mid_01","RT_mid_02","RT_mid_03","RT_mid_04"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_SingleJoint(module_name="RT_handCup", side="LF", joint="RT_handCup", control_shape="Cylinder", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_Finger(module_name="RT_ring", side="RT", joints=["RT_ring_01","RT_ring_02","RT_ring_03","RT_ring_04"], child_of="RT_clavicle_cc", constrained_to="RT_handCup")
    self.make_Finger(module_name="RT_pinkie", side="RT", joints=["RT_pinkie_01","RT_pinkie_02","RT_pinkie_03","RT_pinkie_04"], child_of="RT_clavicle_cc", constrained_to="RT_handCup")
    self.make_Finger(module_name="RT_thumb", side="RT", joints=["RT_thumb_01","RT_thumb_02","RT_thumb_03"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")

    # SwordAttach (for controlling both the sword and sheith at the same time)
    swordAttach = self.make_SingleJoint(joint="swordAttach", module_name="SwordAttach", side="LF", control_shape="Cylinder")
    swordAttach.setup_multi_follow(control="swordAttach_cc", targets=["pelvis", "RT_wrist", "LF_wrist"], module=swordAttach.node)
    cmds.addAttr("swordAttach_cc", longName="showSword", attributeType="long", defaultValue=1, keyable=True, min=0, max=1)
    cmds.connectAttr("swordAttach_cc.showSword", "sword_geo.visibility")
    cmds.connectAttr("swordAttach_cc.showSword", "sheath_geo.visibility")
    cmds.connectAttr("swordAttach_cc.showSword", "strap_geo.visibility")

    # sword
    sword = self.make_SingleJoint(joint="sword", module_name="Sword", side="LF", control_shape="Cylinder", child_of="pelvis_cc", constrained_to="swordAttach_cc")
    sword.setup_multi_follow(control="sword_cc", targets=["swordAttach", "pelvis", "RT_wrist", "LF_wrist"], module=sword.node)
    # sheith
    sheath = self.make_SingleJoint(joint="sheath", module_name="Sheath", side="LF", control_shape="Cylinder")
    sheath.setup_multi_follow(control="sheath_cc", targets=["swordAttach", "pelvis", "RT_wrist", "LF_wrist"], module=sheath.node)

    # pistol
    pistol = self.make_FkHierarchy(startJoint="pistol", module_name="Pistol", side=None, control_shape="Cube")
        
    for i in range(1, 9):
        self.make_SingleJoint(joint="swordStrap_0{0}".format(i), module_name="swordStrap_0{0}".format(i), side=None, control_shape="Cube")

    # mantle 
    self.make_FkChain(joints=["LF_mantleFront_01", "LF_mantleFront_02"], module_name="LF_mantleFront", side="LF", control_shape="Cube")
    self.make_FkChain(joints=["LF_mantleSide_01", "LF_mantleSide_02", "LF_mantleSide_03"], module_name="LF_mantleSide", side="LF", control_shape="Cube")
    cmds.parentConstraint("LF_upArmTwist_01", "LF_mantleSide_01_cc_grp", mo=1)
    self.make_FkChain(joints=["LF_mantleRear_01", "LF_mantleRear_02", "LF_mantleRear_03"], module_name="LF_mantleRear", side="LF", control_shape="Cube")
    
    self.make_FkChain(joints=["ctr_mantle_01", "ctr_mantle_02", "ctr_mantle_03"], module_name="ctr_mantle", side="c", control_shape="Cube")

    self.make_FkChain(joints=["RT_mantleFront_01", "RT_mantleFront_02"], module_name="RT_mantleFront", side="RT", control_shape="Cube")
    self.make_FkChain(joints=["RT_mantleSide_01", "RT_mantleSide_02", "RT_mantleSide_03"], module_name="RT_mantleSide", side="RT", control_shape="Cube")
    cmds.parentConstraint("RT_upArmTwist_01", "RT_mantleSide_01_cc_grp", mo=1)
    self.make_FkChain(joints=["RT_mantleRear_01", "RT_mantleRear_02", "RT_mantleRear_03"], module_name="RT_mantleRear", side="RT", control_shape="Cube")

    # outer skirt
    self.make_FkChain(joints=["LF_skirt_01", "LF_skirt_02", "LF_skirt_03", "LF_skirt_04"], module_name="LF_skirt", side="LF", child_of="pelvis_cc", constrained_to="LF_upLegTwist_01")
    self.make_FkChain(joints=["RT_skirt_01", "RT_skirt_02", "RT_skirt_03", "RT_skirt_04"], module_name="RT_skirt", side="RT", child_of="pelvis_cc", constrained_to="RT_upLegTwist_01")

    # inner skirt
    self.make_SingleJoint(joint="peltFront", module_name="peltFront", side="c", control_shape="Cube")

    self.make_SingleJoint(joint="LF_peltFlap", module_name="LF_peltFlap", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_peltFlap", module_name="RT_peltFlap", side="RT", control_shape="Cube")
    
    self.make_SingleJoint(joint="peltRear", module_name="peltRear", side="c", control_shape="Cube")
    
    self.make_SingleJoint(joint="LF_skirtRear_01", module_name="LF_skirtRear_01", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="LF_skirtRear_02", module_name="LF_skirtRear_02", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_skirtRear_01", module_name="RT_skirtRear_01", side="RT", control_shape="Cube")
    self.make_SingleJoint(joint="RT_skirtRear_02", module_name="RT_skirtRear_02", side="RT", control_shape="Cube")

    self.make_SingleJoint(joint="LF_skirtFlap", module_name="LF_skirtFlap", side="LF", control_shape="Cube")
    self.make_SingleJoint(joint="RT_skirtFlap", module_name="RT_skirtFlap", side="RT", control_shape="Cube")
   
    self.make_SingleJoint(joint="skirtRear", module_name="skirtRear", side="c", control_shape="Cube")

    self.make_SingleJoint(joint="beltBuckle", module_name="beltBuckle", side="c", control_shape="Cube")

    self.make_SingleJoint(joint="LF_kneepad", module_name="LF_kneepad", side="LF", control_shape="Cube", child_of="cog_cc", constrained_to="LF_loLeg")
    self.make_SingleJoint(joint="RT_kneepad", module_name="RT_kneepad", side="RT", control_shape="Cube", child_of="cog_cc", constrained_to="RT_loLeg")

    cmds.addAttr("cog_cc", ln="showSkirt", dv=1, at="bool", k=1)
    vis_grp = ["outerSkirt_geo", "LF_skirtRear_01_cc_grp", "LF_skirtRear_02_cc_grp", "skirtRear_cc_grp", "LF_skirt_01_cc_grp"]
    for node in vis_grp:
        cmds.connectAttr("cog_cc.showSkirt", "{0}.visibility".format(node))
        if "LF_" in node:
            cmds.connectAttr("cog_cc.showSkirt", "{0}.visibility".format(node.replace("LF_", "RT_")))

    # face
    jaw = self.make_FkHierarchy(startJoint="jaw", module_name="Jaw", side="c", control_shape="Cube")
    midHead = self.make_FkHierarchy(startJoint="midHead", module_name="MidHead", side="c", control_shape="Cube")
    upHead = self.make_FkHierarchy(startJoint="upHead", module_name="upHead", side="c", control_shape="Cube")

    # setup extra facial controls
    cmds.parent("upLip_cc_grp", "head_cc")
    cmds.parent("LF_brow_cc_grp", "RT_brow_cc_grp","LF_upLid_cc_grp" , "RT_upLid_cc_grp", "LF_loLid_cc_grp", "RT_loLid_cc_grp","upHead_cc", a=1)
    cmds.parent("loLip_cc_grp", "jaw_cc")
    cmds.parent("LF_naslab_cc_grp", "RT_naslab_cc_grp", "head_cc")
    cmds.parent("LF_mouthCorner_cc_grp", "RT_mouthCorner_cc_grp", "jaw_cc", a=1)

    cmds.parent("LF_upLid_01_cc_grp","LF_upLid_02_cc_grp","LF_upLid_03_cc_grp", "LF_upLid_cc")
    cmds.parent("RT_upLid_01_cc_grp","RT_upLid_02_cc_grp","RT_upLid_03_cc_grp", "RT_upLid_cc")

    cmds.parent("LF_loLid_01_cc_grp","LF_loLid_02_cc_grp","LF_loLid_03_cc_grp", "LF_loLid_cc")
    cmds.parent("RT_loLid_01_cc_grp","RT_loLid_02_cc_grp","RT_loLid_03_cc_grp", "RT_loLid_cc")

    cmds.parent("LF_brow_01_cc_grp", "LF_brow_02_cc_grp", "LF_brow_03_cc_grp", "LF_brow_cc")
    cmds.parent("RT_brow_01_cc_grp", "RT_brow_02_cc_grp", "RT_brow_03_cc_grp", "RT_brow_cc")

    upLip_cc = ["LF_upLip_01_cc_grp", "LF_upLip_02_cc_grp",
                "RT_upLip_01_cc_grp", "RT_upLip_02_cc_grp", 
                "upLipMid_cc_grp"] 

    for ctrl in upLip_cc:
        cmds.parentConstraint("upLip_cc", ctrl, mo=1)

    loLip_cc = ["LF_loLip_01_cc_grp", "LF_loLip_02_cc_grp",
                "RT_loLip_01_cc_grp", "RT_loLip_02_cc_grp",
                "loLipMid_cc_grp"]

    for ctrl in loLip_cc:
        cmds.parentConstraint("loLip_cc", ctrl, mo=1)

    cmds.parent("eyes_grp", "head_cc")
    const = cmds.parentConstraint("worldSpace", "eyes_space", mo=1)
    cmds.connectAttr("eyes_cc.Follow", const[0] + ".worldSpaceW0")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    cmds.refresh()

    cmds.parent("geometry", "root", "Reyda_grp")
    cmds.parent("exclude", "rig")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.hide("exclude")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl", noRecurse=True)

    scale_exclude = ["head_cc", "upHead_cc", "jaw_cc", "nose_cc",
                    "upLip_cc", "loLip_cc", "LF_brow_cc", "RT_brow_cc",
                    "LF_upLid_cc", "LF_loLid_cc", "RT_upLid_cc", "Rt_loLid_cc"]

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      parent = cmds.listRelatives(cmds.listRelatives(obj, parent=True)[0], parent=True)
      if parent:
        grandParent = cmds.listRelatives(parent[0], parent=True) 
        if grandParent and grandParent[0] not in scale_exclude:
          cmds.setAttr(obj + ".sx", l=1, cb=0, k=0)
          cmds.setAttr(obj + ".sy", l=1, cb=0, k=0)
          cmds.setAttr(obj + ".sz", l=1, cb=0, k=0)

    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    for ctrl in ['LF_nostril_cc', 'RT_nostril_cc', 'nose_cc', 'browMid_cc', 'LF_midCheek_01_cc', 'LF_midCheek_02_cc', 'LF_midCheek_03_cc', 'LF_upCheek_01_cc', 'LF_upCheek_02_cc', 'LF_upCheek_03_cc', 'LF_lidCorner_in_cc', 'LF_lidCorner_out_cc', 'LF_browbone_01_cc', 'LF_browbone_02_cc', 'LF_browbone_03_cc', 'LF_ear_cc', 'RT_midCheek_01_cc', 'RT_midCheek_02_cc', 'RT_midCheek_03_cc', 'RT_upCheek_01_cc', 'RT_upCheek_02_cc', 'RT_upCheek_03_cc', 'RT_lidCorner_in_cc', 'RT_lidCorner_out_cc', 'RT_browbone_01_cc', 'RT_browbone_02_cc', 'RT_browbone_03_cc', 'RT_ear_cc', 'LF_brow_01_cc', 'LF_brow_02_cc', 'LF_brow_03_cc', 'RT_brow_01_cc', 'RT_brow_02_cc', 'RT_brow_03_cc', 'LF_upLid_01_cc', 'LF_upLid_02_cc', 'LF_upLid_03_cc', 'RT_upLid_01_cc', 'RT_upLid_02_cc', 'RT_upLid_03_cc', 'LF_loLid_01_cc', 'LF_loLid_02_cc', 'LF_loLid_03_cc', 'RT_loLid_01_cc', 'RT_loLid_02_cc', 'RT_loLid_03_cc', 'tongue_cc', 'loLipMid_cc', 'chin_cc', 'LF_loCheek_01_cc', 'LF_loCheek_02_cc', 'LF_jowl_01_cc', 'LF_jowl_02_cc', 'LF_loLip_01_cc', 'LF_loLip_02_cc', 'LF_loLip_03_cc', 'RT_loCheek_01_cc', 'RT_loCheek_02_cc', 'RT_jowl_01_cc', 'RT_jowl_02_cc', 'RT_loLip_01_cc', 'RT_loLip_02_cc', 'RT_loLip_03_cc', 'upLipMid_cc', 'LF_naslab_01_cc', 'LF_naslab_02_cc', 'LF_upLip_01_cc', 'LF_upLip_02_cc', 'LF_upLip_03_cc', 'RT_naslab_01_cc', 'RT_naslab_02_cc', 'RT_upLip_01_cc', 'RT_upLip_02_cc', 'RT_upLip_03_cc']:
        sdk = cmds.group(em=1, name=ctrl + "_sdk")
        cmds.delete(cmds.parentConstraint(ctrl, sdk, mo=0))
        cmds.parent(sdk, ctrl + "_grp", a=1)
        cmds.parent(ctrl, sdk, a=1)

    cmds.select(cl=1)


    # version off the body_rig file
    body_rig_path = r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\rig data\versions\body_rig"

    if not os.path.exists(body_rig_path):
        os.mkdir(body_rig_path)
        

    body_rig_file = r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\rig data\Reyda_bodyRig.ma"

    if os.path.exists(body_rig_file):
        # version it off
        num_files = len(os.listdir(body_rig_path))
        shutil.copy(body_rig_file, os.path.join(body_rig_path, os.path.basename(body_rig_file)[0:-3] + "_00" + str(num_files + 1) + ".ma"))

    cmds.file(rename=r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\rig data\Reyda_bodyRig.ma")

    cmds.file(save=True, options="v=0", type="mayaAscii", force=True)

    cmds.file(r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\rig data\Reyda_facekeys.ma", open=True, force=True)

    # remove the namespace
    cmds.file(cmds.file(reference=True, q=1)[0], importReference=True)
    cmds.namespace(set=":")
    cmds.namespace(removeNamespace="Reyda_bodyRig", mergeNamespaceWithRoot=True)

    face.setup_face_rig()

    cmds.playbackOptions(min=1, max=24)

    cmds.select(cl=1)

    # version the rig file
    anim_rig_path = r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\rig data\versions\anim_rig"

    if not os.path.exists(anim_rig_path):
        os.mkdir(anim_rig_path)

    anim_rig_file = r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\Reyda_animRig.ma"

    if os.path.exists(anim_rig_file):
        # version it off
        num_files = len(os.listdir(anim_rig_path))
        shutil.copy(anim_rig_file, os.path.join(anim_rig_path, os.path.basename(anim_rig_file)[0:-3] + "_00" + str(num_files + 1) + ".ma"))

    # save the file
    cmds.file(rename=r"D:\Documents\Google Drive\01 BFA\Thesis Project Local Files\Rig\Final Rig\Reyda_Rig\scenes\Reyda_animRig.ma")
    cmds.file(save=True, options="v=0", type="mayaAscii", force=True)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

