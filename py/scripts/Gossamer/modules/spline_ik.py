import maya.cmds as cmds
import Gossamer.modules.module as module
reload(module)
import Gossamer.library.control_curves as control_curves
import operator

class SplineIK(module.Module):
  """A simple module for creating fk controls from an input joint chain. 
  
  Args:
    char_node (str): The name of the CharNode that this module will get connected to.\n
    node (str): If given, the class will be constructed from the data of an existing Module node. (non-functional)\n
    name (str): The name to give the module. The suffix "_module" will be appended to this for the network node.\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    *Accepts ["l", "L", "lf", "LF", "r","R","rt","RT","c","C","ctr", " ", None]*
    module_type (str): The class type for this module.

  Attributes:
    contract (list): ["ikJoints"]\n
    * Accepts *n* number of input joints. 

  """

  contract = ["ikJoints"]

  def __init__(self, char_node=None, node=None, name="ikChain1", side=None, control_shape="Cube"):
    super(SplineIK, self).__init__(char_node, node, name, side, module_type="SplineIK", control_shape=control_shape)

    self.make_contract(SplineIK.contract)

  @classmethod
  def set_bind_joints(cls, ikChain_node, joints):
    """Designates a given joints as ikJoints, fulfilling this Module's contract.\n

    Args:
      ikChain_node (str): The name of the ikChain node to connect these joints to.\n
      joints (str): A DAG of joints. 

    """

    for joint in joints:
      if "module" not in cmds.listAttr(joint):
        cmds.addAttr(joint, attributeType="message", longName="module")
        cmds.addAttr(joint, attributeType="message", longName="ikJoint")
        cmds.addAttr(joint, attributeType="message", longName="component")


      cmds.connectAttr("{0}.bindJoints".format(ikChain_node),
                       "{0}.module".format(joint), force=True)

      cmds.connectAttr("{0}.ikJoints".format(ikChain_node),
                       "{0}.ikJoint".format(joint), force=True)

  @classmethod
  def build_controls(cls, ikChain_node, stretchy=False, num_controls=3):
    """Builds the controls on the module if the contract has been fulfilled. Finds and sorts the input joint chain 
    by the length of their relatives. 

    Args:
      ikChain_node (str): The name of the ikChain node to add these controls to. \n
    """

    cls.make_ik_system(ikChain_node, stretchy=stretchy)
    cls.make_control_joints(ikChain_node, num_controls=num_controls)

  @classmethod
  def make_ik_system(cls, ikChain_node, stretchy=True):
    ikJoints = cmds.listConnections("{0}.ikJoints".format(ikChain_node))
    # sort the DAG chain using a depth method
    joint_and_num_relatives = {}
    for joint in ikJoints:
      relatives = cmds.listRelatives(joint, allDescendents=1)
      if relatives:
        joint_and_num_relatives[joint] = len(relatives)
      else:
        joint_and_num_relatives[joint] = 0

    # sorts the dictionary by its second entry, reverses it, and then creates a list from its first item
    sorted_ikJoints = [i for i, j in sorted(joint_and_num_relatives.items(), key=operator.itemgetter(1))[::-1]]

    if ikJoints:
      # make spline ik curve
      linear_curve = cmds.curve(point=[tuple(cmds.xform(jnt, q=1, t=1, ws=1)) for jnt in sorted_ikJoints], degree=1)
      # that curve is accurate to our joints but isn't a bezier curve. Let's fit one to it
      curve = cmds.fitBspline(tolerance=0.1, name=ikChain_node + "_crv", constructionHistory=False)[0]
      cmds.delete(linear_curve)

      cmds.addAttr(curve, at="message", ln="module")
      cmds.addAttr(ikChain_node, at="message", ln="curve")
      cmds.connectAttr(ikChain_node + ".curve", curve + ".module")
      # make spline IK
      spline_ik = cmds.ikHandle(solver="ikSplineSolver", startJoint=sorted_ikJoints[0], endEffector=sorted_ikJoints[-1], ccv=False, curve=curve, name=ikChain_node + "_sik")
      cmds.addAttr(spline_ik[0], at="message", ln="module")
      cmds.addAttr(ikChain_node, at="message", ln="ikHandle")
      cmds.connectAttr(ikChain_node + ".ikHandle", spline_ik[0] + ".module")

      cmds.parent(curve, world=True)


      if stretchy:
        curve_info = cmds.shadingNode("curveInfo", name=ikChain_node + "_curveInfo", asUtility=True)
        cmds.connectAttr(cmds.pickWalk(curve, d="down")[0] + ".local", curve_info + ".inputCurve")
        stretch_factor = cmds.shadingNode("multDoubleLinear", asUtility=True, name=ikChain_node + "_curveStretchFactor")

        cmds.connectAttr(curve_info + ".arcLength", stretch_factor + ".input1")
        cmds.setAttr(stretch_factor + ".input2", 1.0 / float(cmds.getAttr(curve_info + ".arcLength")))

        for i in range(len(sorted_ikJoints)):
          md = cmds.shadingNode("multDoubleLinear", asUtility=True, name=sorted_ikJoints[i] + "_stretch_mdl")
          cmds.setAttr(md + ".input1", cmds.getAttr(sorted_ikJoints[i] + ".tx"))
          cmds.connectAttr(stretch_factor + ".output", md + ".input2")
          cmds.connectAttr(md + ".output", sorted_ikJoints[i] + ".tx")

  @classmethod
  def make_control_joints(cls, ikChain_node, num_controls=3):
    # make the control joints that will be skinned to the curve
    curve = cmds.listConnections(ikChain_node + ".curve")[0]
    curve_shape = cmds.pickWalk(curve, d="down")[0]

    curve_joints = []
    control_groups = []

    # create our joints
    for i in range(num_controls):
      cmds.select(clear=True)
      joint = cmds.joint(name=cmds.getAttr(ikChain_node + ".name") + "_" + str(i + 1))
      tmp_point_on_curve_info = cmds.createNode("pointOnCurveInfo")
      cmds.connectAttr(curve_shape + ".worldSpace[0]", tmp_point_on_curve_info + ".inputCurve")
      cmds.setAttr(tmp_point_on_curve_info + ".turnOnPercentage", 1)
      cmds.setAttr(tmp_point_on_curve_info + ".parameter", i / float(num_controls - 1))

      control = cls.build_control_from_attr(mod_node=ikChain_node, name=joint + "_cc", scale=1)
      control_grp = cmds.group(control, name=joint + "_grp")

      cmds.addAttr(joint, longName="component", attributeType="message")
      cmds.addAttr(control[0], longName="bindJoint", attributeType="message")
      cmds.connectAttr(joint + ".component", control[0] + ".bindJoint")

      cmds.setAttr(control_grp + ".tx", cmds.getAttr(tmp_point_on_curve_info + ".result.position.positionX"))
      cmds.setAttr(control_grp + ".ty", cmds.getAttr(tmp_point_on_curve_info + ".result.position.positionY"))
      cmds.setAttr(control_grp + ".tz", cmds.getAttr(tmp_point_on_curve_info + ".result.position.positionZ"))

      cmds.parentConstraint(control, joint, maintainOffset=False)

      cmds.delete(tmp_point_on_curve_info)

      curve_joints.append(joint)
      control_groups.append(control_grp)

      cls.add_component(ikChain_node, control[0])
      cls.add_component(ikChain_node, joint)


    cmds.select(curve_joints, replace=True)
    cmds.select(curve, add=True)
    cmds.skinCluster(toSelectedBones=True, name=ikChain_node + "_skinCluster", maximumInfluences=4, dropoffRate=6.0)

    to_dnt = cmds.group(curve_joints, curve, cmds.listConnections(ikChain_node + ".ikHandle")[0], name=ikChain_node + "_grp")
    cmds.hide(to_dnt)


    char_node = cls.get_char_node(ikChain_node)
    root_node = cmds.listConnections("{0}.root".format(char_node))[0]
    dnt_grp = cmds.listConnections("{0}.dntGrp".format(root_node))[0]

    cmds.parent(to_dnt, dnt_grp)

