import maya.cmds as cmds
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module
reload(module) 
import operator

class Ribbon(module.Module):
  contract = ["nurbsPlane", "jointParent"]


  def __init__(self, char_node=None, node=None, name="ribbon1", side=None, control_shape="Cube", joint_parent="chest"):
    super(Ribbon, self).__init__(char_node, node, name, side, module_type="Ribbon", control_shape=control_shape)      

    self.make_contract(Ribbon.contract)

    cmds.addAttr(joint_parent, attributeType="message", longName="ribbonParent")
    cmds.connectAttr("{0}.{1}".format(self.node, Ribbon.contract[1]), "{0}.ribbonParent".format(joint_parent))

    root = cmds.listConnections("{0}.root".format(self.get_char_node(self.node)))[0]
    joint_parent_component = cmds.listConnections("{0}.component".format(joint_parent))

    control_grp = cmds.group(empty=True, name=name + "_control_grp", parent=joint_parent_component[0])
    cmds.addAttr(control_grp, attributeType="message", longName="controlGroup")
    cmds.addAttr(self.node, attributeType="message", longName="controlGroup")
    cmds.connectAttr("{0}.controlGroup".format(self.node), "{0}.controlGroup".format(control_grp))

    drive_grp = cmds.group(empty=True, name=name + "_drive_grp", parent=cmds.listConnections("{0}.dntGrp".format(root))[0])
    cmds.addAttr(drive_grp, attributeType="message", longName="driveGroup")
    cmds.addAttr(self.node, attributeType="message", longName="driveGroup")
    cmds.connectAttr("{0}.driveGroup".format(self.node), "{0}.driveGroup".format(drive_grp))

    cmds.hide(drive_grp)

  @classmethod
  def build_nurbs_plane(cls, ribbon_node, custom_plane=None):
    if not custom_plane:
      plane = cmds.nurbsPlane(pivot=(0,0,0), axis=(0,0,0), width=10, lengthRatio=.1, patchesU=20, patchesV=2, degree=3, constructionHistory=False)[0]
      plane_shape = cmds.pickWalk(plane, d="down")[0]
      plane = [plane, plane_shape]
    else:
      plane_shape = cmds.pickWalk(custom_plane, d="down")[0]
      plane = [custom_plane, plane_shape]

    cls.add_component(ribbon_node, plane[0])
    # add custom attributes to plane to connect it to the module
    cmds.addAttr(plane[1], longName="module", attributeType="message")
    cmds.connectAttr("{0}.{1}".format(ribbon_node, Ribbon.contract[0]), "{0}.module".format(plane[1]))

    cmds.parent(plane[0], cmds.listConnections("{0}.driveGroup".format(ribbon_node)))

  @classmethod
  def build_drive_joints(cls, ribbon_node, name_prefix="strap", num_bind_joints=7):
    plane = cmds.listConnections("{0}.nurbsPlane".format(ribbon_node))

    cmds.addAttr(ribbon_node, longName="driveJoints", attributeType="message")

    drive_jnt_grp = cmds.group(empty=True, name=name_prefix + "_grp")

    if not len(plane):
      return

    for i in range(num_bind_joints):
      cmds.select(cl=1)

      joint = cmds.joint(name="{0}{1}_drive".format(name_prefix, (i + 1)), radius=1.5)

      # connect it to the module
      cmds.addAttr(joint, longName="module", attributeType="message")
      cmds.connectAttr("{0}.driveJoints".format(ribbon_node), "{0}.module".format(joint))

      info_node = cmds.createNode("pointOnSurfaceInfo", name=joint + "_pointOnSurfaceInfo")
      cmds.connectAttr("{0}.worldSpace[0]".format(plane[0]), info_node + ".inputSurface")
      cmds.setAttr(info_node + ".turnOnPercentage", 1)

      cmds.setAttr(info_node + ".parameterV", 0.5)

      if i != 0:
          cmds.setAttr(info_node + ".parameterU", (1 / (float(num_bind_joints - 1)) * i))
      else:
          cmds.setAttr(info_node + ".parameterU", 0)

      # make a matrix rivot
      matrix_4x4 = cmds.shadingNode("fourByFourMatrix", name=joint + "_fourByFourMatrix", asUtility=True)
      i = 0
      j = 0
      info_attrs = ["normalizedNormal", "normalizedTangentU", "normalizedTangentV", "position"]
      axis = ["X", "Y", "Z"]

      for i in range(4):
        for j in range(3):
          cmds.connectAttr("{0}.{1}{2}".format(info_node, info_attrs[i], axis[j]), "{0}.in{1}{2}".format(matrix_4x4, i, j))

      decompose_matrix = cmds.createNode("decomposeMatrix", name=joint + "_decomposeMatrix")
      cmds.connectAttr(matrix_4x4 + ".output", decompose_matrix + ".inputMatrix")
      cmds.connectAttr(decompose_matrix + ".outputTranslate", joint + ".translate")
      cmds.connectAttr(decompose_matrix + ".outputRotate", joint + ".rotate")

      cmds.parent(joint, drive_jnt_grp)

    cmds.parent(drive_jnt_grp, cmds.listConnections("{0}.driveGroup".format(ribbon_node)))

  @classmethod
  def build_control_joints(cls, ribbon_node, name_prefix="strap", num_control_joints=4):

    #todo: replace joint shape with custom control shape

    plane = cmds.listConnections("{0}.nurbsPlane".format(ribbon_node))

    cmds.addAttr(ribbon_node, longName="controlJoints", attributeType="message")

    if not len(plane):
      return

    control_joints = []
    control_jnt_grp = cmds.group(empty=True, name=name_prefix + "_grp")

    for i in range(num_control_joints):
      cmds.select(cl=1)

      joint = cmds.joint(name="{0}{1}_cc".format(name_prefix, (i + 1)))

      # connect it to the module
      cmds.addAttr(joint, longName="controlJoints", attributeType="message")
      cmds.connectAttr("{0}.controlJoints".format(ribbon_node), "{0}.controlJoints".format(joint))

      info_node = cmds.createNode("pointOnSurfaceInfo", name=joint + "_pointOnSurfaceInfo")
      cmds.connectAttr("{0}.worldSpace[0]".format(plane[0]), info_node + ".inputSurface")
      cmds.setAttr(info_node + ".turnOnPercentage", 1)

      cmds.setAttr(info_node + ".parameterV", .5)

      if i != 0:
          cmds.setAttr(info_node + ".parameterU", (1 / (float(num_control_joints - 1)) * i))
      else:
          cmds.setAttr(info_node + ".parameterU", 0)

      # make a matrix rivot
      matrix_4x4 = cmds.shadingNode("fourByFourMatrix", name=joint + "_fourByFourMatrix", asUtility=True)
      i = 0
      j = 0
      info_attrs = ["normalizedNormal", "normalizedTangentU", "normalizedTangentV", "position"]
      axis = ["X", "Y", "Z"]

      for i in range(4):
        for j in range(3):
          cmds.connectAttr("{0}.{1}{2}".format(info_node, info_attrs[i], axis[j]), "{0}.in{1}{2}".format(matrix_4x4, i, j))

      decompose_matrix = cmds.createNode("decomposeMatrix", name=joint + "_decomposeMatrix")
      cmds.connectAttr(matrix_4x4 + ".output", decompose_matrix + ".inputMatrix")

      # make orient and sdk groups
      joint_loc = cmds.xform(joint, q=1, t=1, ws=1)

      orient_grp = cmds.group(joint, name=joint + "_grp")
      cmds.xform(orient_grp, pivots=[joint_loc[0],joint_loc[1],joint_loc[2]], ws=1)
      sdk_grp = cmds.group(joint, name=joint + "_sdk")
      cmds.xform(sdk_grp, pivots=[joint_loc[0],joint_loc[1],joint_loc[2]], ws=1)

      cmds.parent(orient_grp, control_jnt_grp)

      axis = ["X", "Y", "Z"]

      for i in range(3):
        cmds.setAttr(orient_grp + ".translate{0}".format(axis[i]), cmds.getAttr(decompose_matrix + ".outputTranslate.outputTranslate{0}".format(axis[i])))
        cmds.setAttr(orient_grp + ".rotate{0}".format(axis[i]), cmds.getAttr(decompose_matrix + ".outputRotate.outputRotate{0}".format(axis[i])))
      
      control_joints.append(joint)

      cmds.delete(decompose_matrix, matrix_4x4, info_node)

    cls.skin_control_joints(ribbon_node, control_joints, plane[0])

    cmds.parent(control_jnt_grp, cmds.listConnections("{0}.controlGroup".format(ribbon_node)))

  @classmethod
  def build_bind_joints(cls, ribbon_node, custom_joints=None, name_prefix="strap"):
    joint_parent = cmds.listConnections("{0}.jointParent".format(ribbon_node))[0]
    drive_joints = cmds.listConnections("{0}.driveJoints".format(ribbon_node))

    jnt_and_num = {}
    for jnt in drive_joints:
      str_ints = [i for i in jnt if i.isdigit()]
      integers = []
      temp_int = ""
      for j in str_ints:
        temp_int += j
      jnt_and_num[jnt] = int(temp_int)
        
    sorted_jnts = [i for i, j in sorted(jnt_and_num.items(), key=operator.itemgetter(1))[::-1]]

    if not custom_joints:
      for joint in drive_joints:
        bind_joint = cmds.duplicate(joint, name=joint.replace("_drive",""))[0]
        cmds.parent(bind_joint, joint_parent)
        
        # add a drive attribute to the bind joint so that it will get constrained to its drive joint
        cmds.addAttr(joint, longName="drive", attributeType="message")
        cmds.addAttr(bind_joint, longName="drive", attributeType="message")
        cmds.connectAttr("{0}.drive".format(joint), "{0}.drive".format(bind_joint))
        # and connect it to the bindJoints attribute on our network node
        cmds.connectAttr("{0}.bindJoints".format(ribbon_node), "{0}.module".format(bind_joint))
    else:
      for i in range(len(custom_joints)):
        # connect it to the bindJoints attribute on our network node
        cmds.addAttr(custom_joints[i], longName="module", attributeType="message")
        cmds.connectAttr("{0}.bindJoints".format(ribbon_node), "{0}.module".format(custom_joints[i]))
        cmds.parentConstraint(sorted_jnts[i], custom_joints[i], mo=1)

  @classmethod
  def change_joint_shapes(cls, ribbon_node):
    control_joints = cmds.listConnections("{0}.controlJoints".format(ribbon_node))

    for joint in control_joints:
      # set the joint to not draw itself
      cmds.setAttr("{0}.drawStyle".format(joint), 2)
      # create a new control based on the user's desired shape
      ctrl, ctrl_shape = cls.build_control_from_attr(ribbon_node, joint + "_tmp", module.SCALE_CONSTANT * .5)

      cmds.select(ctrl_shape)
      cmds.parent(ctrl_shape, joint, relative=True, shape=True)
      cmds.delete(ctrl)

      cls.add_component(ribbon_node, joint)


  @classmethod
  def skin_control_joints(cls, ribbon_node, joints, nurbsPlane):

    cmds.select(joints, nurbsPlane, replace=True)

    new_cstr = cmds.skinCluster(toSelectedBones=True, skinMethod=0, dropoffRate=3.0)[0]

    cmds.select(nurbsPlane)
    cmds.skinPercent(new_cstr, pruneWeights=0.05)


# myRibbon = Ribbon(char_node="Reyda_CharNode", name="Strap", side=None, joint_parent="chest")
# Ribbon.build_nurbs_plane(myRibbon.node, custom_plane="strap_nurbsPlane")
# Ribbon.build_drive_joints(myRibbon.node)
# Ribbon.build_control_joints(myRibbon.node)
# Ribbon.build_bind_joints(myRibbon.node)
# Ribbon.change_joint_shapes(myRibbon.node)
