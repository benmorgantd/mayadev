import maya.cmds as cmds
import maya.OpenMaya as om
import Gossamer.modules.module as module
reload(module)
import Gossamer.library.control_curves as control_curves
import operator
import json

class FkHierarchy(module.Module):
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

  contract = ["startJoint"]

  def __init__(self, char_node=None, node=None, name="fkHierarchy1", side=None, control_shape="Cube"):
    super(FkHierarchy, self).__init__(char_node, node, name, side, module_type="FkHierarchy", control_shape=control_shape)

    self.make_contract(FkHierarchy.contract)

  @classmethod
  def set_bind_joints(cls, fkHierarchy_node, start_joint=None, stop_at=[]):
    """Designates the given joints as fkJoints, fulfilling this Module's contract.\n

    Args:
      fkHierarchy_node (str): The name of the fkHierarchy node to connect these joints to.\n
      joints (str): A DAG of joints. 

    """

    start_joint = start_joint
    cmds.addAttr(start_joint, attributeType="message", longName="startJoint")
    cmds.connectAttr("{0}.startJoint".format(fkHierarchy_node), "{0}.startJoint".format(start_joint))

    sel = om.MSelectionList()
    sel.add(start_joint)
    dag = om.MDagPath()
    sel.getDagPath(0, dag)

    itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
    itDag.reset(dag, om.MItDag.kDepthFirst, om.MFn.kJoint)

    while not itDag.isDone():
      joint = itDag.partialPathName()

      if joint not in stop_at:
        if "module" not in cmds.listAttr(joint):
          cmds.addAttr(joint, attributeType="message", longName="module")
          cmds.addAttr(joint, attributeType="message", longName="fkJoint")
          cmds.addAttr(joint, attributeType="message", longName="component")

        cmds.connectAttr("{0}.bindJoints".format(fkHierarchy_node),
                         "{0}.module".format(joint), force=True)

      else:
        itDag.prune()

      itDag.next()


  @classmethod
  def build_controls(cls, fkHierarchy_node, child_of=False, constrained_to=False, stop_at=[]):
    """Builds the controls on the module if the contract has been fulfilled. Finds and sorts the input joint chain 
    by the length of their relatives. 

    Args:
      fkHierarchy_node (str): The name of the fkHierarchy node to add these controls to. \n
      child_of (str or False): If given, will force the orient group of the top control to that parent.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy\n
      constrained_to (str or False): If given, will parentConstrain the orient group of the top control to that object.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy.
    
    """

    start_joint = cmds.listConnections("{0}.startJoint".format(fkHierarchy_node))[0]

    sel = om.MSelectionList()
    sel.add(start_joint)
    dag = om.MDagPath()
    sel.getDagPath(0, dag)

    itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
    itDag.reset(dag, om.MItDag.kDepthFirst, om.MFn.kJoint)

    while not itDag.isDone():
      joint = itDag.partialPathName()

      if joint not in stop_at:

        shapeLib.Shape(joint, self.shapeType, jnt=joint)

        cmds.delete(cmds.parentConstraint(joint, cc_grp, mo=0))

        # connect the control to the joint
        cmds.addAttr(cc[0], longName="bindJoint", attributeType="message")
        cmds.connectAttr("{0}.bindJoint".format(cc[0]), "{0}.component".format(joint))

        parent_component = cmds.listConnections("{0}.component".format(cmds.listRelatives(joint, parent=True, type="joint")[0]))[0]
        cmds.parent(cc_grp, parent_component)

      else:
        itDag.prune()

      itDag.next()


    
