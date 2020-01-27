# wtAddMatrix_facerig

import maya.cmds as cmds
import maya.mel as mel
from collections import OrderedDict

POSE_COUNT = 11

FACE_CONTROLS = ['LF_nostril_cc', 'RT_nostril_cc', 'nose_cc', 'browMid_cc', 'LF_midCheek_01_cc', 'LF_midCheek_02_cc', 'LF_midCheek_03_cc', 'LF_upCheek_01_cc', 'LF_upCheek_02_cc', 'LF_upCheek_03_cc', 'LF_lidCorner_in_cc', 'LF_lidCorner_out_cc', 'LF_browbone_01_cc', 'LF_browbone_02_cc', 'LF_browbone_03_cc', 'LF_ear_cc', 'RT_midCheek_01_cc', 'RT_midCheek_02_cc', 'RT_midCheek_03_cc', 'RT_upCheek_01_cc', 'RT_upCheek_02_cc', 'RT_upCheek_03_cc', 'RT_lidCorner_in_cc', 'RT_lidCorner_out_cc', 'RT_browbone_01_cc', 'RT_browbone_02_cc', 'RT_browbone_03_cc', 'RT_ear_cc', 'LF_brow_01_cc', 'LF_brow_02_cc', 'LF_brow_03_cc', 'RT_brow_01_cc', 'RT_brow_02_cc', 'RT_brow_03_cc', 'LF_upLid_01_cc', 'LF_upLid_02_cc', 'LF_upLid_03_cc', 'RT_upLid_01_cc', 'RT_upLid_02_cc', 'RT_upLid_03_cc', 'LF_loLid_01_cc', 'LF_loLid_02_cc', 'LF_loLid_03_cc', 'RT_loLid_01_cc', 'RT_loLid_02_cc', 'RT_loLid_03_cc', 'tongue_cc', 'loLipMid_cc', 'chin_cc', 'LF_loCheek_01_cc', 'LF_loCheek_02_cc', 'LF_jowl_01_cc', 'LF_jowl_02_cc', 'LF_loLip_01_cc', 'LF_loLip_02_cc', 'LF_loLip_03_cc', 'RT_loCheek_01_cc', 'RT_loCheek_02_cc', 'RT_jowl_01_cc', 'RT_jowl_02_cc', 'RT_loLip_01_cc', 'RT_loLip_02_cc', 'RT_loLip_03_cc', 'upLipMid_cc', 'LF_naslab_01_cc', 'LF_naslab_02_cc', 'LF_upLip_01_cc', 'LF_upLip_02_cc', 'LF_upLip_03_cc', 'RT_naslab_01_cc', 'RT_naslab_02_cc', 'RT_upLip_01_cc', 'RT_upLip_02_cc', 'RT_upLip_03_cc']

DRIVERS = OrderedDict()
DRIVERS['LF_mouthCorner_cc'] = ['tx', 2.5,'tx', -2.5,'ty', 2, 'ty',-2]
DRIVERS['LF_naslab_cc'] = ['ty',1]
DRIVERS['jaw_cc'] = ['rx', 25]
DRIVERS['LF_upLid_cc'] = ['rx', 21]
DRIVERS['eyes_cc'] = ['tx', 20,'tx', -20, 'ty', 10, 'ty', -10]

def store_neutral_pose():
  for control in FACE_CONTROLS:
    # create its weighted add matrix node
    wt_add_matrix = cmds.shadingNode("wtAddMatrix", name=control + "_wtAddMatrix", asUtility=True)
    
    cmds.setAttr("{0}_wtAddMatrix.wtMatrix[0].matrixIn".format(control),
                cmds.getAttr("{0}.matrix".format(control + "_sdk")), type="matrix")
    # the "default pose" needs to be stored and set to a weight of 1 so that rotations can interpolate
    cmds.setAttr("{0}_wtAddMatrix.wtMatrix[0].weightIn".format(control), 1)

    decomp_matrix = cmds.createNode("decomposeMatrix", name=control + "_decompMatrix")
    cmds.connectAttr(wt_add_matrix + ".matrixSum", decomp_matrix + ".inputMatrix")

    cmds.connectAttr(decomp_matrix + ".outputTranslateX", control + "_sdk" + ".translateX")
    cmds.connectAttr(decomp_matrix + ".outputTranslateY", control + "_sdk" + ".translateY")
    cmds.connectAttr(decomp_matrix + ".outputTranslateZ", control + "_sdk" + ".translateZ")

    # all rotations get averaged out, so this node will multiply it by the sum of the amount of FACS attributes
    rotation_fixer_node = cmds.createNode("multiplyDivide", name=control + "_rotation_md")

    cmds.setAttr(rotation_fixer_node + ".i2x", 1)
    cmds.setAttr(rotation_fixer_node + ".i2y", 1)
    cmds.setAttr(rotation_fixer_node + ".i2z", 1)

    cmds.connectAttr(decomp_matrix + ".outputRotateX", rotation_fixer_node + ".i1x")
    cmds.connectAttr(decomp_matrix + ".outputRotateY", rotation_fixer_node + ".i1y")
    cmds.connectAttr(decomp_matrix + ".outputRotateZ", rotation_fixer_node + ".i1z")

    cmds.connectAttr(rotation_fixer_node + ".ox", control + "_sdk" + ".rotateX")
    cmds.connectAttr(rotation_fixer_node + ".oy", control + "_sdk" + ".rotateY")
    cmds.connectAttr(rotation_fixer_node + ".oz", control + "_sdk" + ".rotateZ")

def store_pose(driver, attr, frame):
  for control in FACE_CONTROLS:
    cmds.setAttr("{0}_wtAddMatrix.wtMatrix[{1}].matrixIn".format(control, frame),
                 cmds.getAttr(control + ".matrix", time=frame), type="matrix")
    cmds.connectAttr("{0}.{1}".format(driver, attr), "{0}_wtAddMatrix.wtMatrix[{1}].weightIn".format(control, frame))

  if "LF_" in driver:
    flip_pose()

    cmds.setAttr("{0}.{1}".format(driver, attr), 0)

    mirror_driver = driver.replace("LF_", "RT_")

    for control in FACE_CONTROLS:
      cmds.setAttr("{0}_wtAddMatrix.wtMatrix[{1}].matrixIn".format(control, frame + POSE_COUNT),
                   cmds.getAttr(control + ".matrix", time=frame), type="matrix")
      cmds.connectAttr("{0}.{1}".format(mirror_driver, attr), "{0}_wtAddMatrix.wtMatrix[{1}].weightIn".format(control, frame + POSE_COUNT))
      

def flip_pose(ns=":"):
  attribute_mirrors = [1, 1, -1, -1, -1, 1]

  for control in FACE_CONTROLS:
    if "LF_" in control:
      k = 0
      for i in ["t", "r"]:
        for j in ["x", "y", "z"]:
          control_value = None
          mirror_control_value = None
          mirror_control = control.replace("LF_", "RT_")

          control_value = cmds.getAttr("{0}{1}.{2}{3}".format(ns,control, i, j), time=cmds.currentTime(q=1))
          mirror_control_value = cmds.getAttr("{0}{1}.{2}{3}".format(ns,mirror_control, i, j), time=cmds.currentTime(q=1))

          cmds.setAttr("{0}{1}.{2}{3}".format(ns,control, i, j), (mirror_control_value * attribute_mirrors[k]))
          cmds.setAttr("{0}{1}.{2}{3}".format(ns,mirror_control, i, j), (control_value * attribute_mirrors[k]))
          
          cmds.setKeyframe(ns + control)
          cmds.setKeyframe(ns + mirror_control)

          k += 1

def setup_face_rig():
  cmds.currentTime(0)
  store_neutral_pose()

  facs_addition_node = cmds.createNode("plusMinusAverage", name="facs_attrSum_pma")
  # we want the rotations to at least be multiplied by 1
  cmds.setAttr(facs_addition_node + ".input1D[0]", 1)

  i = 1

  for driver in DRIVERS:
    for j in range(0, len(DRIVERS[driver]), 2):
      attr = DRIVERS[driver][j]
      val = DRIVERS[driver][j+1]

      cmds.currentTime(i)

      remap = cmds.createNode("remapValue", name="{0}_{1}_sdk_remap".format(driver, attr))
      # check here if value is negative
      cmds.setAttr(remap + ".outputMax", 1.35)
      cmds.setAttr(remap + ".outputMin", 0.0)
      cmds.setAttr(remap + ".inputMin", 0.0)
      cmds.setAttr(remap + ".inputMax", val)
      cmds.connectAttr("{0}.{1}".format(driver, attr), remap + ".inputValue")

      if "LF_" in driver:
        # make the corresponding mirror driver
        mirror_driver = driver.replace("LF_", "RT_")
        mirror_remap = cmds.createNode("remapValue", name="{0}_{1}_sdk_remap".format(mirror_driver, attr))
        # check here if value is negative
        cmds.setAttr(mirror_remap + ".outputMax", 1.35)
        cmds.setAttr(mirror_remap + ".outputMin", 0.0)
        cmds.setAttr(mirror_remap + ".inputMin", 0.0)
        cmds.setAttr(mirror_remap + ".inputMax", val)
        cmds.connectAttr("{0}.{1}".format(mirror_driver, attr), mirror_remap + ".inputValue")

      store_pose(remap, "outValue", i) 
      cmds.connectAttr("{0}.outValue".format(remap), facs_addition_node + ".input1D[{0}]".format(i))
      i += 1


  for node in cmds.ls("*_rotation_md"):
    cmds.connectAttr(facs_addition_node + ".output1D", node + ".i2x")
    cmds.connectAttr(facs_addition_node + ".output1D", node + ".i2y")
    cmds.connectAttr(facs_addition_node + ".output1D", node + ".i2z")

  cmds.currentTime(0)
  cmds.delete(all=True, channels=True, unitlessAnimationCurves=False)


# setup_face_rig()

