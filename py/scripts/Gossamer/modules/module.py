import maya.cmds as cmds
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
reload(control_curves)

SCALE_CONSTANT = 6

class Module(object):
  """The base class for all modules of the rig. Modules are self-contained parts of the rig that are built from a skeleton hierarchy.
  Modules store metadata pertaining to the component. Its "variables" are accessed via message attribute connections.

  Args:
    char_node (str): The name of the CharNode that this module will get connected to.\n
    node (str): If given, the class will be constructed from the data of an existing Module node. (non-functional)\n
    name (str): The name to give the module. The suffix "_module" will be appended to this for the network node.\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    *Accepts ["l", "L", "lf", "LF", "r","R","rt","RT","c","C","ctr", " ", None]*\n
    module_type (str): The class type for this module.\n
    control_shape (str): Used by some child classes to build custom control shapes where applicable. \n
    *Accepts ["Cube", "Circle","Triangle", "Square", "IK", "4-Sided Arrow", "Circular 4-Sided Arrow", "Sphere", "Dome", "Cylinder", "Circle Stick"]*
  \n
  Attributes:
    node (str): The name of pre-existing Module node.\n
    name (str): The name to give the module.\n
    char_node (str): The name of the Character node to connect this module to.\n
    type (str): This node's type. Default is "Module".\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    type (str): The class type for this module.\n
    control_shape (str): Used by some child classes to build custom control shapes where applicable. \n
    components (list): A list containing the components connected to this module\n
    bind_joints (list): A list containing the bind joints connected to this module.

  """

  control_shapes = ["Cube", "Circle","Triangle", "Square", "IK", "4-Sided Arrow", "Circular 4-Sided Arrow", "Sphere", "Dome", "Cylinder", "Circle Stick"]

  def __init__(self, char_node=None, node=None, name="module", side=None, module_type="", control_shape="Cube"):
    self.node = node
    self.char_node = char_node
    self.name = name
    self.side = side
    self.components = []
    self.bind_joints = []
    self.type = module_type
    self.control_shape = control_shape

    self.gather_node_data()

  def gather_node_data(self):
    """Initializes the node with either existing data or with the data passed in the constructor"""

    if self.node:
      # initialize attributes from existing data
      self.char_node = self.get_char_node(self.node)
      self.name = cmds.getAttr("{node}.name".format(node=self.node))
      self.side = cmds.getAttr("{node}.side".format(node=self.node))
      self.components = self.get_components(self.node)
      self.type = cmds.getAttr("{node}.type".format(node=self.node))
    else:
      # create module node
      self.node = cmds.createNode("network", name="{name}_module".format(name=self.name))
      self.add_metadata()
      self.connect_to_char_node()
      self.add_control_types()
      
  def connect_to_char_node(self):
    """Connects this module to the Character node it was passed upon creation"""

    if self.char_node and "isMasterNode" in cmds.listAttr(self.char_node):
      cmds.connectAttr("{char_node}.modules".format(char_node=self.char_node),
                       "{node}.character".format(node=self.node))
    else:
      raise ValueError("Module was not connected to a char_node since no valid one was given.")

  def add_metadata(self):
    """Adds Metadata to rig that can be used by scripts"""

    # store module's side
    cmds.addAttr(self.node, longName="side", dataType="string")
    if self.side:
      cmds.setAttr("{node}.side".format(node=self.node), self.side, type="string", lock=1)

    # store module's name
    cmds.addAttr(self.node, longName="name", dataType="string")
    cmds.setAttr("{node}.name".format(node=self.node), self.name, type="string", lock=1)

    # store module's type
    cmds.addAttr(self.node, longName="type", dataType="string")
    cmds.setAttr("{node}.type".format(node=self.node), self.type, type="string", lock=1)

    # create a message attribute that will connect this module to the Character node
    cmds.addAttr(self.node, attributeType="message", longName="character")

    # create a message attribute that will hold all the module's components
    cmds.addAttr(self.node, attributeType="message", longName="components")

    # create a message attribute that will hold all the module's bind joints
    cmds.addAttr(self.node, attributeType="message", longName="bindJoints")

    # store module's color
    # cmds.addAttr(self.node, longName="color", attributeType="long", defaultValue=0)

    # if self.side:
    #   if self.side in ["l", "L", "lf", "LF", "Left"]:
    #     # blue
    #     cmds.setAttr("{node}.color".format(node=self.node), 6)
    #   elif self.side in ["r", "R","rt","RT", "Right"]:
    #     # red
    #     cmds.setAttr("{node}.color".format(node=self.node), 13)
    #   elif self.side in ["c","C","ctr"," "]:
    #     # yellow (22 or 17 works well)
    #     cmds.setAttr("{node}.color".format(node=self.node), 22)
    # else:
    #   # aqua
    #   cmds.setAttr("{node}.color".format(node=self.node), 23)

  def add_control_types(self):
    """Add an enum attribute that can store the type of control to be used for some of our components"""

    cmds.addAttr(self.node, 
        longName="controlShape", 
        attributeType="enum",
        enumName=":".join(Module.control_shapes))

    cmds.setAttr("{0}.controlShape".format(self.node), Module.control_shapes.index(self.control_shape))

  def make_contract(self, contract):
    """Creates the node's contract from the class's contract attribute. \n
    Contracts must be satisfied for the node to be able to initialize.

    Args:
      contract (list): A list of message attributes to add to the node. 

    """

    if contract[0] not in cmds.listAttr(self.node):
      for i in range(len(contract)):
        cmds.addAttr(self.node, attributeType="message", longName=contract[i])

  @classmethod
  def add_component(cls, mod_node, comp_node):
    """Used by modules to add themselves to the network via message connection. Any DAG object that makes up the "rig" of the \n
    character should be connected to the module's 'components' attribute. 

    Args:
      mod_node (str): The module node to connect to.\n
      comp_node (str): The component (control, group, ikHandle, etc) that is getting connected to the node.

    """ 

    # connect our color value to each of the transform node's shape nodes if it has them
    comp_shapes = cmds.listRelatives(comp_node, type="shape")
    if comp_shapes:

      if "module" not in cmds.listAttr(comp_node):
        cmds.addAttr(comp_node, longName="module", attributeType="message")

      cmds.connectAttr("{node}.components".format(node=mod_node), "{comp}.module".format(comp=comp_node))

      for shape in comp_shapes:
        cmds.setAttr(shape + ".overrideEnabled", 1)
        # cmds.connectAttr(mod_node + ".color", shape + ".overrideColor")

  @classmethod
  def get_components(cls, mod_node):
    """Used by the class to get the nodes connected to its components attribute.
    
    Args:
      mod_node (str): The module to query. 

    """

    return cmds.listConnections(mod_node + ".components")

  @classmethod
  def get_char_node(cls, mod_node):
    """Returns the string representation of the connected char_node.
    
    Args:
      mod_node (str): The module to query.

    """
    return cmds.listConnections("{node}.character".format(node=mod_node))[0]

  @classmethod
  def build_control_from_attr(cls, mod_node, name, scale):
    """Builds a control from the shape toolbox based on the module's control shape attribute

    Args:
      mod_node (str): The module to query.\n
      name (str): The name to give the control.\n
      scale (float): If given, the control shape will be scaled globally. Normally this involves the SCALE_CONSTANT 

    """

    shape_value = Module.control_shapes[cmds.getAttr("{0}.controlShape".format(mod_node))]

    if shape_value == "Cube":
      control = control_curves.cube_ctrl(name, scale)
    elif shape_value == "Triangle":
      control = control_curves.tri_ctrl(name, scale)
    elif shape_value == "Square":
      control = control_curves.square_ctrl(name, scale)
    elif shape_value == "IK":
      control = control_curves.ik_switch_ctrl(name, scale)
    elif shape_value == "4-Sided Arrow":
      control = control_curves.four_arrow_ctrl(name, scale)
    elif shape_value == "Circular 4-Sided Arrow":
      control = control_curves.four_arrow_circle_ctrl(name, scale)
    elif shape_value == "Sphere":
      control = control_curves.sphere_ctrl(name, scale)
    elif shape_value == "Dome":
      control = control_curves.dome_ctrl(name, scale)
    elif shape_value == "Cylinder":
      control = control_curves.hex_cylinder_ctrl(name, scale)
    elif shape_value == "Circle":
      control = control_curves.circle_ctrl(name, scale)
    elif shape_value == "Circle Stick":
      control = control_curves.circle_stick_ctrl(name, scale)

    return control

  @classmethod
  def destroy_controls(cls, mod_node):
    """Disconnect bind joint scales then delete all the components
    
    Args:
      mod_node (str): The module to query.

    """


    bind_joints = cmds.listConnections("{0}.bindJoints".format(mod_node))

    if bind_joints:
      for jnt in bind_joints:
        scale_sources = cmds.listConnections("{0}.scale".format(jnt), destination=True, plugs=True)
        if scale_sources:
          for node in scale_sources:
            if "inverseScale" not in node:
              cmds.disconnectAttr(node, "{0}.scale".format(jnt))

    cmds.delete(cmds.listConnections("{0}.components".format(mod_node)))

  @classmethod
  def echo_data(cls, module):
    """Does a pretty display of the module's attributes and connections.
    
    Args:
      module (str): The module to query.
  
    """

    if "components" in cmds.listAttr(module):
      ctrls = cmds.listConnections("{0}.components".format(module))
      ctrl_set = cmds.sets(ctrls, name=module + "_set")
      # cmds.addAttr(module, ln="ctrlSet")
      char_node = Module.get_char_node(module)
      char_set = cmds.listConnections("{0}.ctrlSet".format(char_node))
      cmds.sets(ctrl_set, include=char_set[0])

      if ctrls:
        for ctrl in ctrls:
          shp_rels = cmds.listRelatives(ctrl, type="shape")
          if shp_rels:
            for shp in cmds.listRelatives(ctrl, type="shape"):
              if "LF_" in ctrl:
                cmds.connectAttr(char_node + ".leftColor", shp + ".overrideColor")
              elif "RT_" in ctrl:
                cmds.connectAttr(char_node + ".rightColor", shp + ".overrideColor")
              elif cmds.getAttr("{0}.side".format(module)) == "c":
                cmds.connectAttr(char_node + ".centerColor", shp + ".overrideColor")
              elif not cmds.getAttr("{0}.side".format(module)):
                cmds.connectAttr(char_node + ".extraColor", shp + ".overrideColor")
    

    print ""
    om.MGlobal.displayInfo("{0} node '{1}' successfully created.".format(cmds.getAttr("{0}.type".format(module)), module))
    for attr in cmds.listAttr(module, userDefined=1):
      try:
        om.MGlobal.displayInfo("{0} : {1}".format(attr, cmds.getAttr("{0}.{1}".format(module, attr))))
      except RuntimeError:
        om.MGlobal.displayInfo("{0} : {1}".format(attr, cmds.listConnections("{0}.{1}".format(module, attr))))
    print ""

    cmds.refresh()
    
  @classmethod
  def setup_world_follow(cls, control=None, constraint_type="parent", defaultValue=1, module=None):
    """Sets up a control to follow the "worldSpace" group from the rig. 
    
    Args:
      module (str): The module to query.\n
      control (str): The control to set up this behavior on. \n
      constraint_type (str): The type of constraint to use. Accepted values are "parent" and "orient"\n
      defaultValue (int): The default value to use for this attribute. 
  
    """

    space_grp = cmds.group(control, name=control + "_space")
    cmds.xform(space_grp, pivots=cmds.xform(control, q=1, t=1, ws=1), ws=1)

    world_space_grp = cmds.listConnections("{0}.worldSpace".format(cls.get_char_node(module)))[0]
    
    if constraint_type == "parent":
      space_const = cmds.parentConstraint(world_space_grp, space_grp, mo=1)
    elif constraint_type == "orient":
      space_const = cmds.orientConstraint(world_space_grp, space_grp, mo=1)

    # add a space switch attribute on the control 
    cmds.addAttr(control, longName="followWorld", attributeType="long", defaultValue=defaultValue, keyable=True, min=0, max=1)
    cmds.connectAttr("{0}.followWorld".format(control), "{0}.{1}W0".format(space_const[0], world_space_grp))

  @classmethod
  def setup_multi_follow(cls, control=None, constraint_type="parent", targets=None, module=None, default_value=0):
    """Sets up a control to be able to switch between following multiple control spaces on the rig. 
    
    Args:
      module (str): The module to query.\n
      control (str): The control to set up this behavior on. \n
      constraint_type (str): The type of constraint to use. Accepted values are "parent" and "orient"\n
      defaultValue (int): The default value to use for this attribute. 
  
    """

    if not targets:
      return

    space_grp = cmds.group(control, name=control + "_space")
    cmds.xform(space_grp, pivots=cmds.xform(control, q=1, t=1, ws=1), ws=1)

    world_space_grp = cmds.listConnections("{0}.worldSpace".format(cls.get_char_node(module)))[0]
    
    for target in targets:
      if constraint_type == "parent":
        space_const = cmds.parentConstraint(target, space_grp, mo=1, weight=0.0)
      elif constraint_type == "orient":
        space_const = cmds.orientConstraint(target, space_grp, mo=1, weight=0.0)

    if constraint_type == "parent":
      space_const = cmds.parentConstraint(world_space_grp, space_grp, mo=1, weight=0.0)
    elif constraint_type == "orient":
      space_const = cmds.orientConstraint(world_space_grp, space_grp, mo=1, weight=0.0)
    
    constraint_targets = targets + [world_space_grp]

    cmds.addAttr(control, attributeType="enum", longName="follow", defaultValue=default_value, enumName=":".join(constraint_targets), keyable=True)

    for i in range(len(constraint_targets)):
      for j in range(len(constraint_targets)):
        driven_value = 0.0
        if j == i:
          driven_value= 1.0

        cmds.setDrivenKeyframe(space_const[0],
                               attribute="{0}W{1}".format(constraint_targets[i], i),
                               currentDriver="{0}.follow".format(control),
                               inTangentType="plateau",
                               outTangentType="plateau",
                               driverValue=j,
                               value=driven_value)