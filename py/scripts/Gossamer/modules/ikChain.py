import maya.cmds as cmds
import maya.mel
import Gossamer.modules.module as module
reload(module)
import Gossamer.library.control_curves as control_curves
import operator

class IkChain(module.Module):
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

  contract = ["startJoint", "endJoint"]

  def __init__(self, char_node=None, node=None, name="ikChain1", side=None, control_shape="Cube"):
    super(IkChain, self).__init__(char_node, node, name, side, module_type="IkChain", control_shape=control_shape)

    self.make_contract(IkChain.contract)

  @classmethod
  def set_bind_joints(cls, ikChain_node, startJoint, endJoint):
    """Designates a given joints as ikJoints, fulfilling this Module's contract.\n

    Args:
      ikChain_node (str): The name of the ikChain node to connect these joints to.\n
      joints (str): A DAG of joints. 

    """

    rel = cmds.listRelatives(startJoint, ad=1, type="joint")
    rel.reverse()

    cmds.addAttr(startJoint, ln="startJoint", at="message")
    cmds.connectAttr(ikChain_node + ".startJoint", startJoint + ".startJoint")

    for joint in rel:
      if joint != endJoint:
        if "module" not in cmds.listAttr(joint):
          cmds.addAttr(joint, attributeType="message", longName="module")
          cmds.addAttr(joint, attributeType="message", longName="component")

        cmds.connectAttr("{0}.bindJoints".format(ikChain_node),
                         "{0}.module".format(joint), force=True)

      else:
        if "module" not in cmds.listAttr(joint):
          cmds.addAttr(joint, attributeType="message", longName="module")
          cmds.addAttr(joint, attributeType="message", longName="component")

        cmds.connectAttr("{0}.bindJoints".format(ikChain_node),
                         "{0}.module".format(joint), force=True)

        cmds.addAttr(joint, ln="endJoint", at="message")
        cmds.connectAttr(ikChain_node + ".endJoint", joint + ".endJoint")

        break

  @classmethod
  def build_controls(cls, ikChain_node, child_of=False, joints=[], constrained_to=False, sol="ikSpringSolver"):
    """Builds the controls on the module if the contract has been fulfilled. Finds and sorts the input joint chain 
    by the length of their relatives. 

    Args:
      ikChain_node (str): The name of the ikChain node to add these controls to. \n
      child_of (str or False): If given, will force the orient group of the top control to that parent.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy\n
      constrained_to (str or False): If given, will parentConstrain the orient group of the top control to that object.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy.
    
    """


    startJoint = cmds.listConnections(ikChain_node + ".startJoint")[0]
    endJoint = cmds.listConnections(ikChain_node + ".endJoint")[0]

    ikJoints = []

    for jnt in joints:
      cmds.select(clear=True)
      dup = cmds.duplicate(jnt, name=jnt + "_ik", parentOnly=1, renameChildren=1)[0]
      ikJoints.append(dup)

    for i in range(len(joints)):
      original_chain_parent = cmds.listRelatives(joints[i], parent=True, type="joint")[0]
      if original_chain_parent + "_ik" in cmds.ls(type="joint"):
        cmds.parent(ikJoints[i], original_chain_parent + "_ik")


    ikJoints_grp = cmds.group(startJoint + "_ik", name=ikJoints[0] + "_grp")

    controls = []

    ikHandle = cmds.ikHandle(sj=startJoint + "_ik", ee=endJoint + "_ik", sol="ikRPsolver", name=endJoint[0:-3] + "_rpik")

    # if sol == "ikSpringSolver":
    #   maya.mel.eval("ikSpringSolver;")
    #   cmds.ikHandle(ikHandle[0], edit=True, sol="ikSpringSolver")

    controls.append(ikHandle)

    handleGrp = cmds.group(ikHandle[0], name=ikHandle[0] + "_grp")

    cc = IkChain.build_control_from_attr(ikChain_node, name=endJoint[0:-3] + "_cc", scale=module.SCALE_CONSTANT * .25)
    cc_grp = cmds.group(cc, name = "{0}_grp".format(cc[0]))
    cmds.xform(cc_grp, pivots=cmds.xform(cc[0], q=1, t=1))
    controls.append(cc)

    cmds.delete(cmds.pointConstraint(endJoint, cc_grp, mo=0))

    # create a pole vector control
    pv = IkChain.build_control_from_attr(ikChain_node, name=endJoint[0:-3] + "_pv_cc", scale=module.SCALE_CONSTANT * .25)
    pv_grp = cmds.group(pv, name = "{0}_grp".format(pv[0]))
    cmds.xform(cc_grp, pivots=cmds.xform(pv[0], q=1, t=1))
    controls.append(pv)
    cmds.delete(cmds.parentConstraint(startJoint, pv_grp, mo=0))
    # get second joint's translate
    second_joint_translate = cmds.xform(cmds.listRelatives(startJoint, type="joint")[0], q=1, t=1)
    cmds.xform(pv_grp, t=[second_joint_translate[0] * 1.75, second_joint_translate[1] * 1.75, second_joint_translate[2] * 1.75],
               r=1, os=1)

    module_grp = cmds.group(handleGrp, ikJoints_grp, name=ikChain_node)
    cmds.parent(module_grp, "doNotTouch")

    cmds.parentConstraint(cc[0], handleGrp, mo=1)
    cmds.poleVectorConstraint(pv[0], ikHandle[0]) # springIK solvers don't like pole vector constraints

    cmds.parent(cc_grp, pv_grp, "layout_cc")

    cmds.parentConstraint(cmds.listRelatives(startJoint, parent=True, type="joint")[0], ikJoints_grp, mo=1)

    for jnt in ikJoints:
      cmds.parentConstraint(jnt, jnt.replace("_ik", ""), mo=1)

    for cc in controls:
      cmds.setAttr(cc[0] + ".rx", l=1, k=0)
      cmds.setAttr(cc[0] + ".ry", l=1, k=0)
      cmds.setAttr(cc[0] + ".rz", l=1, k=0)

    for cc in controls:
      cls.add_component(ikChain_node, cc[0])