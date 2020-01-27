import maya.cmds as cmds
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module
reload(module)

class Root(module.Module):
  """A subclass of Module for making the root of a rig. The Root class is unique to other modules in that it 
  has no contract. The joints and controls will be built by the module itself and will be placed centered at the origin. 
  
  Args:
    char_node (str): The name of the CharNode that this module will get connected to.\n
    node (str): If given, the class will be constructed from the data of an existing Module node. (non-functional)\n
    name (str): The name to give the module. The suffix "_module" will be appended to this for the network node.\n
    side (str): The side of the module. Used as the name prefix and also determines control color. \n
    *Accepts ["l", "L", "lf", "LF", "r","R","rt","RT","c","C","ctr", " ", None]*
    
  Attributes:
    name (str): The name to give the module.\n
    char_node (str): The name of the Character node to connect this module to.\n
    type (str): This node's type. Default is "Module".\n
    bind_joints (list): A list containing the bind joints connected to this module.\n

  """

  def __init__(self, char_node=None, node=None, name="root", side="c"):
    super(Root, self).__init__(char_node, node, name, side, module_type="Root")

    if "root" not in cmds.listAttr(self.node):
      cmds.addAttr(self.node, longName="root", attributeType="message")
      cmds.connectAttr("{0}.root".format(char_node), "{0}.root".format(self.node))

    # rig groups
    self.all_grp = None

    # joints
    self.root_joint = None
    self.layout_joint = None
    self.bind_joints = []

    # controls
    self.root_cc = None
    self.root_cc_grp = None
    self.layout_cc = None
    self.layout_cc_grp = None

    if "rigGrp" not in cmds.listAttr(self.node):
      self.make_rig_groups()
      self.add_bind_joints()
    

  def make_rig_groups(self):
    """Makes group hierarchy structure for the character. This includes the Top Node, the doNotTouch group,
     and spaces like the worldSpace group. Each of these is accessible from the module as an attribute. 

     """

    char_node = self.get_char_node(self.node)

    all_grp = cmds.group(empty=1, parent=cmds.listConnections("{0}.topNode".format(char_node))[0], name="rig")

    cmds.addAttr(self.node, attributeType="message", longName="rigGrp")
    cmds.addAttr(all_grp, attributeType="message", longName="module")
    cmds.connectAttr("{0}.rigGrp".format(self.node),
                     "{0}.module".format(all_grp))

    dnt_grp = cmds.group(empty=1, parent=all_grp, name="doNotTouch")

    cmds.addAttr(self.node, attributeType="message", longName="dntGrp")
    cmds.addAttr(dnt_grp, attributeType="message", longName="module")
    cmds.connectAttr("{0}.dntGrp".format(self.node),
                     "{0}.module".format(dnt_grp))

    worldSpace = cmds.group(empty=1, parent=dnt_grp, name="worldSpace")
    cmds.addAttr(char_node, attributeType="message", longName="worldSpace")
    cmds.addAttr(worldSpace, attributeType="message", longName="module")
    cmds.connectAttr("{0}.worldSpace".format(char_node),
                     "{0}.module".format(worldSpace))


    # lock and hide transform attributes
    for a in ["t","r","s"]:
      for x in ["x","y","z"]:
        cmds.setAttr("{0}.{1}{2}".format(all_grp, a, x), lock=1, keyable=0, channelBox=0)

  def add_bind_joints(self):
    """Adds the root and layout joints and connects them to the node."""

    cmds.select(clear=1)
    self.root_joint = cmds.joint(name="root")
    self.layout_joint = cmds.joint(name="layout")
    self.bind_joints += [self.root_joint, self.layout_joint]

    for jnt in self.bind_joints:
      cmds.addAttr(jnt, attributeType="message", longName="module")
      cmds.connectAttr("{0}.bindJoints".format(self.node),
                       "{0}.module".format(jnt))

      cmds.addAttr(jnt, attributeType="message", longName="component")

  @classmethod
  def build_controls(cls, root_node):
    """Buils the control curves for the Root module. The control curves will be triangular in shape.
    This function will also connect those controls to the node.  
    
    Args:
      root_node (str): The name of the root node module to build the controls on. 

    """

    root_cc = control_curves.tri_ctrl(name="root_cc", scale=module.SCALE_CONSTANT * 2.5)
    layout_cc = control_curves.tri_ctrl(name="layout_cc", scale=module.SCALE_CONSTANT * 2)

    root_cc_grp = cmds.group(root_cc, name=root_cc[0] + "_grp")
    layout_cc_grp = cmds.group(layout_cc[0], name=layout_cc[0] + "_grp")
    cmds.parent(layout_cc_grp, root_cc[0])

    # lock visibility attributes on our layout control
    cmds.setAttr(layout_cc[0] + ".v", lock=1, k=0, cb=0)

    cmds.setAttr(root_cc[0] + ".v", lock=1, k=0, cb=0)

    cmds.parent(root_cc_grp, cmds.listConnections("{0}.rigGrp".format(root_node)))

    cmds.addAttr(root_cc[0], attributeType="message", longName="bindJoint")
    cmds.connectAttr("{0}.bindJoint".format(root_cc[0]), "{0}.component".format("root"))
    
    cmds.addAttr(layout_cc[0], attributeType="message", longName="bindJoint")
    cmds.connectAttr("{0}.bindJoint".format(layout_cc[0]), "{0}.component".format("layout"))

    # parent world space group to the root control
    world_space_grp = cmds.listConnections("{0}.worldSpace".format(cls.get_char_node(root_node)))[0]
    cmds.parentConstraint(root_cc[0], world_space_grp, mo=1)

    cls.add_component(root_node, root_cc[0])
    cls.add_component(root_node, layout_cc[0])
    cls.add_component(root_node, layout_cc_grp)
    cls.add_component(root_node, root_cc_grp)
