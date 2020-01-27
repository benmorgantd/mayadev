import maya.cmds as cmds
import Gossamer.modules.module as module
reload(module)
import Gossamer.library.twist_extract as twist_extract
reload(twist_extract)
import maya.OpenMaya as om

#zyx is a good rotate order for forearm twist joints

class Twist(module.Module):
  """A module for making twist joint setups using either the Quaternion or IK extraction methods. 

  Args:
    char_node (str): The name of the CharNode that this module will get connected to.\n
    node (str): If given, the class will be constructed from the data of an existing Module node. (non-functional)\n
    name (str): The name to give the module. The suffix "_module" will be appended to this for the network node.\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    *Accepts ["l", "L", "lf", "LF", "r","R","rt","RT","c","C","ctr", " ", None]*
    
  Attributes:
    contract (list): ["twistJoint"]
    
  """


  contract = ["twistJoint"]

  def __init__(self, char_node=None, node=None, name="quatTwist", side="lf"):
    super(Twist, self).__init__(char_node, node, name, side, module_type="Twist")

    self.make_contract(Twist.contract)


  @classmethod
  def set_bind_joint(cls, joint, twist_node):
    """Designates the given joint as the twist joint for the module. 
  
    Args:
      joint (str): The joint to add to the module. This joint will be used for extractiing twist. 
      twist_node (str): The node to add the joint to. 
    """

    existing_bindJoints = cmds.listConnections("{0}.bindJoints".format(twist_node))

    if not existing_bindJoints:
      # if the joint isn't already a twistJoint
      if Twist.contract[0] not in cmds.listAttr(joint):
        cmds.addAttr(joint, attributeType="message", longName=Twist.contract[0])
        cmds.connectAttr("{0}.{1}".format(twist_node,  Twist.contract[0]),"{0}.{1}".format(joint,Twist.contract[0]))
      else:
        try:
          cmds.connectAttr("{0}.bindJoints".format(twist_node),"{0}.module".format(joint))
        except RuntimeError:
          pass
        try:
          cmds.connectAttr("{0}.{1}".format(twist_node,  Twist.contract[0]),"{0}.{1}".format(joint,Twist.contract[0]))
        except RuntimeError:
          pass
    else:
      try:
        cmds.connectAttr("{0}.{1}".format(twist_node,  Twist.contract[0]),"{0}.{1}".format(joint,Twist.contract[0]))
      except RuntimeError:
        pass


  @classmethod
  def build_twist(cls, twist_node=None, extraction_type="quaternion", start_joint=None, ik_parent=None, twist_joint_parent=None, axis="X"):
    """Using the existing twist joint, sets up the extraction method for getting that joint's true twist value. 
    
    Args:
      twist_node (str): The twist node to use to gather the necessary data. 
      extraction_type (str): The method to use to extract the twist. Valid entires are "quaternion" and "scik". 

      * The Quaternion method is a solid method to use for twist extraction on the twist, neck, and lower leg.

      * The SingleChainIK (scik) method is a solid method to use for twist extraction on the upper arm and leg.

      start_joint (str): Required for the scik method. This joint will be the base of or single chain IK system. 
      ik_parent (str): Required for the scik method. The resulting IK handle will eventually be the child of this joint.
      * It's recommended that you don't use a "bind" joint for this. Try to keep your bind hierarchy clean :)

      twist_joint_parent (str): Required for the scik method. The parent joint of the base of the IK chain. \n
      axis (str): Accepts ["X", "Y", "Z"]. The axis to extract the twist from in Quaternion extraction. 

    """


    if not twist_node:
      return

    twist_joint = cmds.listConnections("{0}.twistJoint".format(twist_node))

    if len(twist_joint) == 1:
      if extraction_type == "quaternion":
        quat_to_euler_node = twist_extract.quat_twist_extract(twist_joint[0], axis)
        cmds.addAttr(twist_node, longName="quatToEulerNode", attributeType="message")
        cmds.addAttr(quat_to_euler_node, longName="quatToEulerNode", attributeType="message")
        Twist.add_component(twist_node, quat_to_euler_node)
        cmds.connectAttr("{0}.quatToEulerNode".format(twist_node), "{0}.quatToEulerNode".format(quat_to_euler_node))

      elif extraction_type == "scik":
        if not start_joint or not ik_parent or not twist_joint_parent:
          om.MGlobal.displayError("Not enough information given to Twist.build_twist()")
          return

        startJoint, ik = twist_extract.ik_twist_extract(twist_joint=twist_joint[0], start_joint=start_joint, ik_parent=ik_parent, twist_joint_parent=twist_joint_parent, name=twist_joint[0])
        
        if "scik" not in cmds.listAttr(twist_node):
          cmds.addAttr(twist_node, longName="scik", attributeType="message")
        if "extractionJoint" not in cmds.listAttr(twist_node):
          cmds.addAttr(twist_node, longName="extractionJoint", attributeType="message")

        cmds.addAttr(ik[0], longName="scik", attributeType="message")
        cmds.addAttr(startJoint, longName="extractionJoint", attributeType="message")
        cmds.connectAttr("{0}.scik".format(twist_node), "{0}.scik".format(ik[0]))
        cmds.connectAttr("{0}.extractionJoint".format(twist_node), "{0}.extractionJoint".format(startJoint))
        Twist.add_component(twist_node, ik[0])

      else:
        om.MGlobal.displayError("Incorrect extraction type. Possible options are 'quaternion' and 'scik'")

    else:
      om.MGlobal.displayError("{0} does not have a twist joint connected.".format(twist_node))
      return

  @classmethod
  def connect_to_twist_joints(cls, joints, twist_node, multiplier=1, axis="X", limb_module=None):
    """Distributes the extracted twist value to the given joints using a linear falloff method. 
    
    Args:
      twist_node (str): The twist node to use to gather the necessary data. \n
      axis (str): Accepts ["X", "Y", "Z"]. The axis to extract the twist from in Quaternion extraction.\n 
      multiplier (float): A global multiplier to use on the extracted value.

      * Useful in cases like the neck where you only have a single twist joint.

    """
    
    joint_count = len(joints)

    if joint_count == 0:
      om.MGlobal.displayError("Must pass at least 1 twist joint")
      return

    # check if the node has had its twist setup done yet
    if "quatToEulerNode" in cmds.listAttr(twist_node):
      extract_node = cmds.listConnections("{0}.quatToEulerNode".format(twist_node))
      extract_attr = "outputRotate.outputRotate{0}".format(axis)
    elif "extractionJoint" in cmds.listAttr(twist_node):
      extract_node = cmds.listConnections("{0}.extractionJoint".format(twist_node))
      extract_attr = "rotate{0}".format(axis)

    else:
      om.MGlobal.displayError("Incorrect contract for twist joint setup.")

    # add manual twist attributes to the given control
    if limb_module:
      control_attribute_names = ["wristFk", "footFk"]
      fk_control_attr = control_attribute_names[cmds.getAttr("{0}.type".format(limb_module)) is "IkFkLeg"]

      fk_control = cmds.listConnections("{0}.{1}".format(limb_module, fk_control_attr))[0]
      ik_control = cmds.listConnections("{0}.ikControl".format(limb_module))[0]
      ik_switch = cmds.listConnections("{0}.ikSwitch".format(limb_module))[0]

      cmds.addAttr(fk_control, longName="Auto_Twist", attributeType="enum", defaultValue=0, en="On:Off", keyable=True)
      cmds.addAttr(fk_control, longName="Twist", attributeType="float", defaultValue=0, keyable=True)

      cmds.addAttr(ik_control, longName="Auto_Twist", attributeType="enum", defaultValue=0, en="On:Off", keyable=True)
      cmds.addAttr(ik_control, longName="Twist", attributeType="float", defaultValue=0, keyable=True)

      # add a condition node that will switch the twist and auto twist values depending on the current loLimb control
      condition = cmds.shadingNode("condition", name="{0}_control_cond".format(twist_node), asUtility=True)
      cmds.connectAttr("{0}.ikFk".format(ik_switch), "{0}.firstTerm".format(condition))

      cmds.connectAttr("{0}.Auto_Twist".format(fk_control), "{0}.cfr".format(condition))
      cmds.connectAttr("{0}.Twist".format(fk_control), "{0}.cfg".format(condition))

      cmds.connectAttr("{0}.Auto_Twist".format(ik_control), "{0}.ctr".format(condition))
      cmds.connectAttr("{0}.Twist".format(ik_control), "{0}.ctg".format(condition))

    # just linear falloff type
    # another good equation is y = -x^1.5 + 1
    x = 1 / float(joint_count)

    if len(extract_node):
      for i in range(len(joints)):
        if limb_module:
          # for blending between manual and auto twist mode
          blend_two_attr = cmds.shadingNode("blendTwoAttr", name="{0}_blend".format(joints[i]), asUtility=True)
          cmds.connectAttr("{0}.{1}".format(extract_node[0], extract_attr), "{0}.input[0]".format(blend_two_attr))
          cmds.connectAttr("{0}.ocg".format(condition), "{0}.input[1]".format(blend_two_attr))
          cmds.connectAttr("{0}.ocr".format(condition), "{0}.attributesBlender".format(blend_two_attr))

        mdl = cmds.shadingNode("multDoubleLinear", name="{0}_mdl".format(joints[i]), asUtility=True)
        cmds.setAttr("{0}.input2".format(mdl), ((-1 * x * i) + 0.9) * multiplier)

        if limb_module:
          cmds.connectAttr("{0}.output".format(blend_two_attr), "{0}.input1".format(mdl))
        else:
          cmds.connectAttr("{0}.{1}".format(extract_node[0], extract_attr), "{0}.input1".format(mdl))

        # if the output is not zero...
        if cmds.getAttr("{0}.output".format(mdl)):
          # create an add double linear node to get rid of any starting values on this node (ideally this should not happen)
          adl = cmds.shadingNode("addDoubleLinear", name="{0}_adl".format(joints[i]), asUtility=True)
          cmds.connectAttr("{0}.output".format(mdl), "{0}.input1".format(adl))
          cmds.setAttr("{0}.input2".format(adl), -1 * cmds.getAttr("{0}.input1".format(adl)))
          cmds.connectAttr("{0}.output".format(adl), "{0}.rotateX".format(joints[i]))
        else:
          cmds.connectAttr("{0}.output".format(mdl), "{0}.rotateX".format(joints[i]))

        # add this joint as a bind joint if it isn't already
        if "bindJoint" not in cmds.listAttr(joints[i]):
          cmds.addAttr(joints[i], longName="bindJoint", attributeType="message")
        cmds.connectAttr("{0}.bindJoints".format(twist_node), "{0}.bindJoint".format(joints[i]), force=True)

    else:
      om.MGlobal.displayError("{0} has not been setup for twist yet.".format(twist_node))

