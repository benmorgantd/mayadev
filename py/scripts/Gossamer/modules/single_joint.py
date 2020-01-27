import maya.cmds as cmds
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module
reload(module) 

class SingleJoint(module.Module):
  """A subclass of Module for making single-joint controls. Useful for simple rigs and controls like the cog and pelvis. 
  
  Args:
    char_node (str): The name of the CharNode that this module will get connected to.\n
    node (str): If given, the class will be constructed from the data of an existing Module node. (non-functional)\n
    name (str): The name to give the module. The suffix "_module" will be appended to this for the network node.\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    *Accepts ["l", "L", "lf", "LF", "r","R","rt","RT","c","C","ctr", " ", None]*
    control_shape (str): Used by some child classes to build custom control shapes where applicable. \n
    *Accepts ["Cube", "Circle","Triangle", "Square", "IK", "4-Sided Arrow", "Circular 4-Sided Arrow", "Sphere", "Dome", "Cylinder", "Circle Stick"]*
    
  Attributes:
    node (str): The name of pre-existing Module node.\n
    name (str): The name to give the module.\n
    char_node (str): The name of the Character node to connect this module to.\n
    type (str): This node's type. Default is "Module".\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    type (str): The class type for this module is SingleJoint.\n
    control_shape (str): Used by some child classes to build custom control shapes where applicable. \n
    components (list): A list containing the components connected to this module\n
    bind_joints (list): A list containing the bind joints connected to this module.\n
    contract (list): ["startJoint"]

  """

  
  contract = ["startJoint"]

  def __init__(self, char_node=None, node=None, name="singleJoint1", side=None, control_shape="Cube"):
    super(SingleJoint, self).__init__(char_node, node, name, side, module_type="SingleJoint", control_shape=control_shape)      

    self.make_contract(SingleJoint.contract)

  @classmethod
  def add_bind_joints(cls, singleJoint_node):
    """Adds a joint as a child of the current joint selection and connects the joint to the module.

    Args:
      singleJoint_node (str): The singleJoint module node to add this joint to.

    """

    jnt = cmds.joint(name=cmds.getAttr("{0}.name".format(singleJoint_node)))

    cmds.addAttr(jnt, attributeType="message", longName="module")
    cmds.addAttr(jnt, attributeType="message", longName="startJoint")

    cmds.connectAttr("{0}.bindJoints".format(singleJoint_node),
                     "{0}.module".format(jnt))

    cmds.connectAttr("{0}.startJoint".format(singleJoint_node),
                     "{0}.startJoint".format(jnt))

    cmds.addAttr(jnt, attributeType="message", longName="component")

  @classmethod
  def set_bind_joints(cls, singleJoint_node, jnt):
    """Designates a given joint to fulfill the class's contract instead of creating one.
    
    Args:
      singleJoint_node (str): The singleJoint module node to add this joint to.\n
      jnt (str): The name of the joint to designate. Works best if given its full DAG path.
    
    """

    # check if the joint already has the custom attributes on it
    if "module" not in cmds.listAttr(jnt):
      cmds.addAttr(jnt, attributeType="message", longName="module")
    if "startJoint" not in cmds.listAttr(jnt):
      cmds.addAttr(jnt, attributeType="message", longName="startJoint")
    if "component" not in cmds.listAttr(jnt):
      cmds.addAttr(jnt, attributeType="message", longName="component")
    # connect our joint to this node
    try:
      cmds.connectAttr("{0}.bindJoints".format(singleJoint_node),
                       "{0}.module".format(jnt), force=True)

      cmds.connectAttr("{0}.startJoint".format(singleJoint_node),
                     "{0}.startJoint".format(jnt), force=True)
    except RuntimeError:
      pass  

  @classmethod
  def build_controls(cls, singleJoint_node, child_of=False, constrained_to=False):
    """Builds the controls for the module if the contract has been fulfilled.
    
    Args:
      singleJoint_node (str): The singleJoint module node to add these controls to.\n
      child_of (str or False): If given, will force the orient group of this control to that parent.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy\n
      constrained_to (str or False): If given, will parentConstrain the orient group of this control to that object.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy.


    """

    startJoint = cmds.listConnections("{0}.startJoint".format(singleJoint_node))

    if startJoint and len(startJoint) == 1:
      cc = SingleJoint.build_control_from_attr(singleJoint_node, name="{0}_cc".format(startJoint[0]), scale=module.SCALE_CONSTANT * 1)
      cc_grp = cmds.group(cc[0], name = "{0}_grp".format(cc[0]))

      cmds.setAttr("{0}.rotateOrder".format(cc[0]), cmds.getAttr("{0}.rotateOrder".format(startJoint[0])))
      cmds.setAttr("{0}.v".format(cc[0]), lock=1, k=0, cb=0)

      cmds.delete(cmds.parentConstraint(startJoint[0], cc_grp, mo=0))

      # make certain that our pivots match
      cmds.xform(cc[0], pivots=cmds.xform(cc_grp, q=1, rotatePivot=1, ws=1), ws=1, a=1)

      cmds.addAttr(cc[0], attributeType="message", longName="bindJoint")
      cmds.connectAttr("{0}.component".format(startJoint[0]),
                       "{0}.bindJoint".format(cc[0]))
      
      for comp in [cc[0], cc_grp]:
        cls.add_component(singleJoint_node, comp)

      if child_of:
        cmds.parent(cc_grp, child_of)
      if constrained_to:
        cmds.parentConstraint(constrained_to, cc_grp, mo=1)
      else:
        #find the parent to the singleJoint's control
        startJoint_parent = cmds.listRelatives(startJoint, parent=True)
        if startJoint_parent:
          # we could give a custom parent here
          try:
            startJoint_parent_component = cmds.listConnections("{0}.component".format(startJoint_parent[0]), destination=True)
            cmds.parent(cc_grp, startJoint_parent_component[0])
          except ValueError:
            # no start joint parent component (could be a twist joint)
            pass
