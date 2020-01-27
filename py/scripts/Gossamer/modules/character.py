import json

import maya.cmds as cmds
import maya.OpenMaya as om

import Gossamer.modules.module as module
reload(module)

VERSION = 1.0


class Character(object):
  """The class for the "Master Node" for the rig. All modules will be connected to the network node of this class.\n

  Args:
    name (str): The name of the character. The suffix "_CharNode" will be appended to this for the network node.\n
    node (str): If given, the class will be constructed from the data of an existing Character node. (non-functional)\n

  Attributes:
    node (str): The name of pre-existing Character node.\n
    name (str): The name of the character.\n
    modules (list): An array that will old all of the module nodes connected to this Character.\n
    poses (dict): A dictionary in json format that can hold basic poses such as the default, bind, and rig poses.\n
    top_node (str): The uppermost DAG node in the rig.\n
    type (str): This node's type. Default is "Character".

  """

  def __init__(self, name="Reyda", node=None):
    self.node = node
    self.name = name
    self.modules = []
    self.poses = {}
    self.top_node = None
    self.type = "Character"

    self.gather_node_data()

    if not self.node:
      self.add_metadata()

  def gather_node_data(self):
    """Either inits the node attributes from scratch or sets them from an existing char node"""

    if self.node and "isMasterNode" in cmds.listAttr(self.node):
      # init attributes from existing character node data
      self.top_node = cmds.listConnections("{node}.topNode".format(node=self.node))
      self.modules = cmds.listConnections("{node}.modules".format(node=self.node))
      self.name = cmds.getAttr("{char_node}.characterName".format(char_node=self.node))
      self.poses = cmds.getAttr("{node}.poses".format(node=self.node))
      self.root = cmds.listConnections("{node}.root".format(node=self.node))

    else:
      # create character node
      self.node = cmds.createNode("network", name="{name}_CharNode".format(name=self.name))

      self.top_node = cmds.group(world=True, empty=True, name="{name}_grp".format(name=self.name))
      # create an all group message attribute
      cmds.addAttr(self.node, attributeType="message", longName="topNode")

      # add an identification attribute so we can find this is a Char node
      cmds.addAttr(self.node, attributeType="bool", longName="isMasterNode", defaultValue=True)

      # create component message attribute
      cmds.addAttr(self.node, attributeType="message", longName="modules")

      # create root message attribute
      cmds.addAttr(self.node, attributeType="message", longName="root")

      # connect our character's all group to our master node
      cmds.addAttr(self.top_node, attributeType="message", longName="character")
      cmds.connectAttr(self.node + ".topNode", "{grp}.character".format(grp=self.top_node))

      self.add_metadata()

  def add_metadata(self):
    """Adds Metadata to rig that can be used by scripts"""

    # store rig version number
    cmds.addAttr(self.node, longName="rigVersion", dataType="string")
    cmds.setAttr(self.node + ".rigVersion", str(VERSION), type="string", lock=True)

    # TODO: check version number with online json file

    # store character name
    cmds.addAttr(self.node, longName="characterName", dataType="string")
    cmds.setAttr("{node}.characterName".format(node=self.node), self.name, type="string", lock=True)

    # store character name
    cmds.addAttr(self.node, longName="type", dataType="string")
    cmds.setAttr("{0}.type".format(self.node), self.type, type="string", lock=True)

    # add a string attribute that can hold strings of dictionaries
    cmds.addAttr(self.node, longName="poses", dataType="string")
    cmds.setAttr("{node}.poses".format(node=self.node), "{}", type="string", lock=True)

    # create a set for all the controls
    cmds.select(cl=1)
    ctrl_set = cmds.sets(name=self.name + "_CTRLS")
    cmds.addAttr(self.node, longName="ctrlSet", at="message")
    cmds.connectAttr(self.node + ".ctrlSet", ctrl_set + ".creator")

    # create color attributes
    cmds.addAttr(self.node, longName="rightColor", at="long", dv=13)
    cmds.addAttr(self.node, longName="leftColor", at="long", dv=6)
    cmds.addAttr(self.node, longName="centerColor", at="long", dv=22)
    cmds.addAttr(self.node, longName="extraColor", at="long", dv=14)

  @classmethod
  def add_pose(cls, char_node, pose_name):
    """Adds a pose to our node's pose dictionary. Useful for rigger-facing rig poses. \n

    Looks through each module and stores the keyable attributes for that module's components. 

    Args:
      char_node (str): The Character node to update.\n
      pose_name (str): The name of the pose we want to make.

    """

    pose = {}
    module_connections = cmds.listConnections("{0}.modules".format(char_node))

    for module in module_connections:
      if "components" in cmds.listAttr(module):
        components = cmds.listConnections("{mod}.components".format(mod=module))
        if components:
          for ctrl in components:
            if ctrl.endswith("_cc"):
              attr_values = {}
              for attr in cmds.listAttr(ctrl, keyable=True):
                attr_values[attr] = cmds.getAttr("{0}.{1}".format(ctrl, attr))
              pose[ctrl] = attr_values
    
    cmds.setAttr("{0}.poses".format(char_node), lock=False)
    # parse the existing poses attribute as json so that we can edit it as a dictionary.
    existing_pose_dict = json.loads(cmds.getAttr("{0}.poses".format(char_node)))
    existing_pose_dict[pose_name] = pose

    om.MGlobal.displayInfo("Pose added to {0}".format(char_node))

    cmds.setAttr("{node}.poses".format(node=char_node), json.dumps(existing_pose_dict), type="string")
    cmds.setAttr("{0}.poses".format(char_node), lock=True)

  @classmethod
  def read_pose(cls, char_node, pose_name):
    """Reads a pose from our character's pose dictionary and sets control values accordingly."""

    cmds.setAttr("{0}.poses".format(char_node), lock=False)
    existing_pose_dict =  cmds.getAttr("{0}.poses".format(char_node))
    existing_pose_dict = json.loads(existing_pose_dict)
    
    # check if pose name exists in our poses dictionary
    if pose_name in existing_pose_dict:
      pose = existing_pose_dict[pose_name]
      # if it does, read the data from each control
      for control in pose:
        # set the attribute for each attribute on that control
        for attr in pose[control]:
          attr_val = pose[control][attr]
          try:
            cmds.setAttr(control + "." + attr, attr_val)
          except:
            pass
    else:
      om.MGlobal.displayError("Pose key '{0}' does not exist in '{1}' pose dictionary.".format(pose_name, char_node))

    cmds.setAttr("{0}.poses".format(char_node), lock=True)

  @classmethod
  def get_modules(cls, char_node):
    """Returns the connections to this node's "modules" attribute.
    
    Args:
      char_node (str): The name of the character node to query.

    """

    return cmds.listConnections("{node}.modules".format(node=char_node))

  @classmethod
  def connect_bind_joints(cls, char_node):
    """Connects all module bind joints to their respective control or drive joint.\n
    Connections done via parentConstraints and scale direct connections.
    
    Args:
      char_node (str): The name of the Character node to query. 
    
    """

    modules = cls.get_modules(char_node)

    if not modules:
      om.MGlobal.displayError("Character has no modules connected. Cannot connect bind joints.")
      return

    # go through each module
    for module in modules:
      # if that module has bindJoint connections
      if "bindJoints" in cmds.listAttr(module) and cmds.listConnections("{0}.bindJoints".format(module)):
        # go through each joint in bindJoints
        for jnt in cmds.listConnections("{0}.bindJoints".format(module)):
          # if that joint has a "drive" attribute and something is connected to it.
          if "drive" in cmds.listAttr(jnt) and "_end" not in jnt:
            drive_joint = cmds.listConnections("{0}.drive".format(jnt), destination=True)
            if drive_joint:
              try:
                cmds.connectAttr("{0}.scale".format(drive_joint[0]), "{0}.scale".format(jnt), force=True)
              except RuntimeError:
                om.MGlobal.displayInfo("{0} Failed to connect scale.".format(jnt))
              cmds.parentConstraint(drive_joint, jnt, maintainOffset=False)

            # otherwise connect that joint to its component
            elif "component" in cmds.listAttr(jnt):
              component = cmds.listConnections("{0}.component".format(jnt))
              if component:
                try:
                  cmds.connectAttr("{0}.scale".format(component[0]), "{0}.scale".format(jnt), force=True)
                except RuntimeError:
                  om.MGlobal.displayInfo("{0} Failed to connect scale.".format(jnt))
                cmds.parentConstraint(component, jnt, maintainOffset=False)
          
          elif "component" in cmds.listAttr(jnt):
              component = cmds.listConnections("{0}.component".format(jnt))
              if component:
                try:
                  cmds.connectAttr("{0}.scale".format(component[0]), "{0}.scale".format(jnt), force=True)
                except RuntimeError:
                  om.MGlobal.displayInfo("{0} Failed to connect scale.".format(jnt))
                cmds.parentConstraint(component, jnt, maintainOffset=False)

  @classmethod
  def disconnect_bind_joints(cls, char_node):
    """Disconnects all bind joints from their respective controls.

    Args:
      char_node (str): The name of the Character node to query. 

    """

    for module in Character.get_modules(char_node):
      if "bindJoints" in cmds.listAttr(module) and cmds.listConnections("{0}.bindJoints".format(module)):
          for jnt in cmds.listConnections("{0}.bindJoints".format(module)):
            cmds.delete(jnt, constraints=1)
            # and disconnect scale connections
            scale_connection = cmds.listConnections("{0}.scale".format(jnt), destination=True)
            if scale_connection:
              cmds.disconnectAttr("{0}.scale".format(scale_connection[0]), "{0}.scale".format(jnt))


