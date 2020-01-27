import maya.cmds as cmds
import Gossamer.modules.module as module
reload(module)
import Gossamer.library.control_curves as control_curves
import operator

class FkChain(module.Module):
  """A simple module for creating fk controls from an input joint chain. 
  
  Args:
    char_node (str): The name of the CharNode that this module will get connected to.\n
    node (str): If given, the class will be constructed from the data of an existing Module node. (non-functional)\n
    name (str): The name to give the module. The suffix "_module" will be appended to this for the network node.\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    *Accepts ["l", "L", "lf", "LF", "r","R","rt","RT","c","C","ctr", " ", None]*
    module_type (str): The class type for this module.

  Attributes:
    contract (list): ["fkJoints"]\n
    * Accepts *n* number of input joints. 

  """

  contract = ["fkJoints"]

  def __init__(self, char_node=None, node=None, name="fkChain1", side=None, control_shape="Cube"):
    super(FkChain, self).__init__(char_node, node, name, side, module_type="FkChain", control_shape=control_shape)

    self.make_contract(FkChain.contract)

  @classmethod
  def set_bind_joints(cls, fkChain_node, joints):
    """Designates a given joints as fkJoints, fulfilling this Module's contract.\n

    Args:
      fkChain_node (str): The name of the fkChain node to connect these joints to.\n
      joints (str): A DAG of joints. 

    """

    for joint in joints:
      if "module" not in cmds.listAttr(joint):
        cmds.addAttr(joint, attributeType="message", longName="module")
        cmds.addAttr(joint, attributeType="message", longName="fkJoint")
        cmds.addAttr(joint, attributeType="message", longName="component")

      cmds.connectAttr("{0}.bindJoints".format(fkChain_node),
                       "{0}.module".format(joint), force=True)

      cmds.connectAttr("{0}.fkJoints".format(fkChain_node),
                       "{0}.fkJoint".format(joint), force=True)


  @classmethod
  def build_controls(cls, fkChain_node, child_of=False, constrained_to=False):
    """Builds the controls on the module if the contract has been fulfilled. Finds and sorts the input joint chain 
    by the length of their relatives. 

    Args:
      fkChain_node (str): The name of the fkChain node to add these controls to. \n
      child_of (str or False): If given, will force the orient group of the top control to that parent.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy\n
      constrained_to (str or False): If given, will parentConstrain the orient group of the top control to that object.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy.
    
    """

    fkJoints = cmds.listConnections("{0}.fkJoints".format(fkChain_node))
    # sort a DAG chain using a depth method
    joint_and_num_relatives = {}
    for joint in fkJoints:
      relatives = cmds.listRelatives(joint, allDescendents=1)
      if relatives:
        joint_and_num_relatives[joint] = len(relatives)
      else:
        joint_and_num_relatives[joint] = 0

    # sorts the dictionary by its second entry, reverses it, and then creates a list from its first item
    sorted_fkJoints = [i for i, j in sorted(joint_and_num_relatives.items(), key=operator.itemgetter(1))[::-1]]

    if fkJoints:
      controls = []
      groups = []
      for i in range(0, len(sorted_fkJoints)):
        cc = FkChain.build_control_from_attr(fkChain_node, name="{0}_cc".format(sorted_fkJoints[i]), scale=module.SCALE_CONSTANT * .25)
        cc_grp = cmds.group(cc, name = "{0}_grp".format(cc[0]))
        cmds.xform(cc_grp, pivots=cmds.xform(cc[0], q=1, t=1))
        controls.append(cc)
        groups.append(cc_grp)

        cmds.setAttr("{0}.v".format(cc[0]), lock=1, k=0, cb=0)
        cmds.setAttr("{0}.rotateOrder".format(cc[0]), cmds.getAttr("{0}.rotateOrder".format(sorted_fkJoints[i])))

        cmds.delete(cmds.parentConstraint(sorted_fkJoints[i], cc_grp, mo=0))

        # connect the control to the joint
        cmds.addAttr(cc[0], longName="bindJoint", attributeType="message")
        cmds.connectAttr("{0}.bindJoint".format(cc[0]), "{0}.component".format(sorted_fkJoints[i]))

        if i > 0:
          cmds.parent(cc_grp, controls[i - 1][0])


      if child_of and constrained_to:
        cmds.parent(groups[0], child_of)
        cmds.parentConstraint(constrained_to, groups[0], mo=1)
      else:
        #find the parent to the singleJoint's control
        startJoint_parent = cmds.listRelatives(sorted_fkJoints[0], parent=1)
        if startJoint_parent:
          startJoint_parent_component = cmds.listConnections("{0}.component".format(startJoint_parent[0]))
          if startJoint_parent_component:
            cmds.parent(groups[0], startJoint_parent_component[0])

      for cc in controls:
        cls.add_component(fkChain_node, cc[0])