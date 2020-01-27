import maya.cmds as cmds
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module
reload(module) 

class ScIk(module.Module):
  """A subclass of Module for making Single-Chain IK control systems. Useful in many prop rigs. 
  
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
    type (str): The class type for this module is ScIk.\n
    control_shape (str): Used by some child classes to build custom control shapes where applicable. \n
    components (list): A list containing the components connected to this module\n
    bind_joints (list): A list containing the bind joints connected to this module.\n
    contract (list): ["startJoint"]

  """

  contract = ["startJoint"]

  def __init__(self, char_node=None, node=None, name="scik1", side=None, control_shape="Cylinder"):
    super(ScIk, self).__init__(char_node, node, name, side, module_type="ScIk", control_shape=control_shape)      

    self.make_contract(ScIk.contract)

  @classmethod
  def add_bind_joints(cls, scik_node):
    """Adds a joint as a child of the current joint selection and connects the joint to the module.

    Args:
      scik_node (str): The scik module node to add this joint to.

    """

    jnt = cmds.joint(name=cmds.getAttr("{0}.name".format(scik_node)))

    cmds.addAttr(jnt, attributeType="message", longName="module")
    cmds.addAttr(jnt, attributeType="message", longName="startJoint")

    cmds.connectAttr("{0}.bindJoints".format(scik_node),
                     "{0}.module".format(jnt))

    cmds.connectAttr("{0}.startJoint".format(scik_node),
                     "{0}.startJoint".format(jnt))

    cmds.addAttr(jnt, attributeType="message", longName="component")

  @classmethod
  def set_bind_joints(cls, scik_node, jnt):
    """Designates a given joint to fulfill the class's contract instead of creating one.
    
    Args:
      scik_node (str): The scik module node to add this joint to.\n
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
      cmds.connectAttr("{0}.bindJoints".format(scik_node),
                       "{0}.module".format(jnt), force=True)

      cmds.connectAttr("{0}.startJoint".format(scik_node),
                     "{0}.startJoint".format(jnt), force=True)
    except RuntimeError:
      pass  

  @classmethod
  def build_controls(cls, scik_node, child_of=False, constrained_to=False, down_vector=[-1,0,0]):
    """Builds the controls for the module if the contract has been fulfilled. Builds a main control with an ikHandle control as child.
    
    Args:
      scik_node (str): The scik module node to add these controls to.\n
      child_of (str or False): If given, will force the orient group of this control to that parent.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy\n
      constrained_to (str or False): If given, will parentConstrain the orient group of this control to that object.\n
      * Useful for fixing complex DAG relationships while maintaining a clean bind joint hierarchy.\n
      down_vector (list): The object-space vector relative to the startJoint to add our end effector joint at.

    """

    # builds the controls on the module if the contract has been fulfilled

    bindJoint = cmds.listConnections("{0}.startJoint".format(scik_node))
    root = cmds.listConnections("{0}.root".format(cls.get_char_node(scik_node)))[0]

    if bindJoint and len(bindJoint):
      bindJoint = bindJoint[0]

      cmds.select(cl=1)
      startJoint = cmds.duplicate(bindJoint, parentOnly=True, name="{0}_ik_start".format(bindJoint))
      endJoint = cmds.duplicate(bindJoint, parentOnly=True, name="{0}_ik_end".format(bindJoint))

      cmds.parent(endJoint, startJoint)
      cmds.xform(endJoint, t=down_vector, r=1, os=1)

      scik = cmds.ikHandle(name=bindJoint + "_scik", sj=startJoint[0], ee=endJoint[0], sol="ikSCsolver")

      cmds.group(startJoint, scik[0], name=bindJoint + "_scik_grp", parent=cmds.listConnections("{0}.dntGrp".format(root))[0])

      cmds.addAttr(startJoint, longName="drive", attributeType="message")
      cmds.addAttr(bindJoint, longName="drive", attributeType="message")
      cmds.connectAttr("{0}.drive".format(startJoint[0]), "{0}.drive".format(bindJoint))

      cc = ScIk.build_control_from_attr(scik_node, name="{0}_cc".format(bindJoint), scale=module.SCALE_CONSTANT * 1)
      cc_grp = cmds.group(cc[0], name = "{0}_grp".format(cc[0]))

      cmds.setAttr("{0}.rotateOrder".format(cc[0]), cmds.getAttr("{0}.rotateOrder".format(bindJoint)))
      cmds.setAttr("{0}.v".format(cc[0]), lock=1, k=0, cb=0)

      cmds.delete(cmds.parentConstraint(bindJoint, cc_grp, mo=0))

      # make certain that our pivots match
      cmds.xform(cc[0], pivots=cmds.xform(cc_grp, q=1, rotatePivot=1, ws=1), ws=1, a=1)

      cmds.parentConstraint(cc[0], startJoint, mo=1)

      # "Circular 4-Sided Arrow"
      cmds.setAttr(scik_node + ".controlShape", 6)
      ik_cc = ScIk.build_control_from_attr(scik_node, name="{0}_ik_cc".format(bindJoint), scale=module.SCALE_CONSTANT * 1)
      ik_cc_grp = cmds.group(ik_cc[0], name = "{0}_grp".format(ik_cc[0]))

      cmds.setAttr("{0}.rotateOrder".format(ik_cc[0]), cmds.getAttr("{0}.rotateOrder".format(bindJoint)))
      cmds.setAttr("{0}.v".format(ik_cc[0]), lock=1, k=0, cb=0)

      cmds.delete(cmds.parentConstraint(endJoint[0], ik_cc_grp, mo=0))

      # make certain that our pivots match
      cmds.xform(ik_cc[0], pivots=cmds.xform(ik_cc_grp, q=1, rotatePivot=1, ws=1), ws=1, a=1)

      cmds.parent(ik_cc_grp, cc[0])

      cmds.parentConstraint(ik_cc[0], scik[0], mo=1)

      # setup world follow for the ik control.
      cls.setup_world_follow(control=ik_cc[0], constraint_type="parent", defaultValue=0, module=scik_node)

      cls.add_component(scik_node, cc[0])
      cls.add_component(scik_node, ik_cc[0])
      cls.add_component(scik_node, scik[0])
      cls.add_component(scik_node, startJoint[0])
      cls.add_component(scik_node, endJoint[0])

      cmds.addAttr(cc[0], ln="bindJoint", at="message")
      cmds.connectAttr(cc[0] + ".bindJoint", bindJoint + ".component")

      if child_of and constrained_to:
        cmds.parent(cc_grp, child_of)
        cmds.parentConstraint(constrained_to, cc_grp, mo=1)
      else:
        #find the parent to the singleJoint's control
        startJoint_parent = cmds.listRelatives(bindJoint, parent=True)
        if startJoint_parent:
          # we could give a custom parent here
          startJoint_parent_component = cmds.listConnections("{0}.component".format(startJoint_parent[0]), destination=True)
          if len(startJoint_parent_component):
            cmds.parent(cc_grp, startJoint_parent_component[0])


            
    cmds.xform(cc[0], pivots=cmds.xform(cc_grp, q=1, rotatePivot=1, ws=1), ws=1, a=1)