import maya.cmds as cmds
import Gossamer.modules.module as module
reload(module)
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
import Gossamer.components.foot as foot
reload(foot)


class Foot(module.Module):
  """A module for making reverse feet. Unique in that it requires some input from a separate module to get fully built.
  
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


  contract = ["foot", "toe", "toeEnd"]

  def __init__(self, char_node=None, node=None, name="foot", side="LF"):
    super(Foot, self).__init__(char_node, node, name, side, module_type="Foot")

    self.make_contract(Foot.contract)

  @classmethod
  def set_bind_joints(cls, foot_node, joints):
    """Set the given joints as the bind joints for the foot node. The top joint should be oriented to the world, 
    and the end joint should be oriented to the world except for its "swivel" axis. 
    
    Args:
      foot_node (str): The node to attach these joints to.
      joints (list): The 3 joints to give for the setup. 
    
    """


    if len(joints) != 3:
      om.MGlobal.displayError("Foot needs 3 joints as an input")
      return

    for i in range(3):
      if i == 0:
        if "footModule" not in cmds.listAttr(joints[i]):
          # to link the foot joint to the footModule (also linked to a leg)
          cmds.addAttr(joints[i], attributeType="message", longName="footModule")
          cmds.connectAttr("{0}.bindJoints".format(foot_node),"{0}.footModule".format(joints[i]))
      else:
        if "module" not in cmds.listAttr(joints[i]):
          cmds.addAttr(joints[i], attributeType="message", longName="module")
          cmds.connectAttr("{0}.bindJoints".format(foot_node),"{0}.module".format(joints[i]))
          cmds.addAttr(joints[i], attributeType="message", longName="ik")
          cmds.addAttr(joints[i], attributeType="message", longName="fk")
          cmds.addAttr(joints[i], attributeType="message", longName="drive")
          cmds.addAttr(joints[i], attributeType="message", longName="component")
      if Foot.contract[i] not in cmds.listAttr(joints[i]):
        cmds.addAttr(joints[i], attributeType="message", longName=Foot.contract[i])
      cmds.connectAttr("{0}.{1}".format(foot_node,  Foot.contract[i]),"{0}.{1}".format(joints[i],Foot.contract[i]), force=True)

  @classmethod
  def set_foot_locators(cls, foot_node, locators):
    """Designates the given locators as the basis for the foot bank and heel roll setup. Uses both the position and orientation. 
    They should be oriented so that the main "action" axis is +rx.
  
    Args:
      foot_node (str): The node to connect these locators to. 
      locators (list): The locators to designate. Typically named ['heel','bankIn','bankOut']

    """

    locator_names = ['heel','bankIn','bankOut']

    if len(locators) != 3:
      om.MGlobal.displayError("Foot needs 3 locators ['heel','bankIn','bankOut'] as an input")
      return

    for i in range(3):
      cmds.addAttr(locators[i], attributeType="message", longName="{0}Loc".format(locator_names[i]))
      cmds.addAttr(foot_node, attributeType="message", longName="{0}Loc".format(locator_names[i]))
      cmds.connectAttr("{0}.{1}Loc".format(foot_node,  locator_names[i]), "{0}.{1}Loc".format(locators[i],  locator_names[i]))

  @classmethod
  def make_joint_chains(cls, foot_node):
    """Creates the ik/fk/drive joint chains for the foot if its contract has been fulfilled. 
    Each joint in the chain gets connected to the foot node. Duplicates the bind joints to do so. 

    Args:
      foot_node (str): The foot node to use. 
    
    """

    setup_joints = []
    joint_attr_names = ["Foot","Toe","ToeEnd"]

    # find our setup joint
    for i in range(len(Foot.contract)):
      joint = cmds.listConnections("{0}.{1}".format(foot_node, Foot.contract[i]))
      if joint and len(joint) == 1:
        setup_joints.append(joint[0])

    foot, toe, toeEnd = setup_joints

    if foot and toe and toeEnd:
      cmds.select(clear=True)
      ik_chain = cmds.duplicate(foot, toe, toeEnd, parentOnly=True, renameChildren=True)
      cmds.select(clear=True)
      fk_chain = cmds.duplicate(foot, toe, toeEnd, parentOnly=True, renameChildren=True)
      cmds.select(clear=True)
      drive_chain = cmds.duplicate(foot, toe, toeEnd, parentOnly=True, renameChildren=True)

      # rename joint chains
      for i in range(2,-1, -1):
        ik_chain[i] = cmds.rename(ik_chain[i], "{0}_rig_{1}".format(setup_joints[i], "ik"))
        fk_chain[i] = cmds.rename(fk_chain[i], "{0}_rig_{1}".format(setup_joints[i], "fk"))
        drive_chain[i] = cmds.rename(drive_chain[i], "{0}_rig_{1}".format(setup_joints[i], "drive"))

        cmds.addAttr(ik_chain[i], attributeType="message", longName="bindJoint") 
        cmds.addAttr(ik_chain[i], attributeType="message", longName="ikJoint") 

        cmds.addAttr(fk_chain[i], attributeType="message", longName="bindJoint") 
        cmds.addAttr(fk_chain[i], attributeType="message", longName="fkJoint") 

        cmds.addAttr(drive_chain[i], attributeType="message", longName="bindJoint")
        cmds.addAttr(drive_chain[i], attributeType="message", longName="driveJoint")

        cmds.connectAttr("{0}.ik".format(setup_joints[i]), "{0}.bindJoint".format(ik_chain[i]))
        cmds.connectAttr("{0}.fk".format(setup_joints[i]), "{0}.bindJoint".format(fk_chain[i]))

        # !! first disconnect the attribute that's tying the leg foot drive to the bind foot!
        existing_bind_foot_drive_connections = cmds.listConnections("{0}.drive".format(setup_joints[i]))
        if existing_bind_foot_drive_connections and len(existing_bind_foot_drive_connections) == 1:
          cmds.disconnectAttr("{0}.drive".format(setup_joints[i]), "{0}.bindJoint".format(existing_bind_foot_drive_connections[0]))

        if i < 2:
          # don't connect the bind joint attribute on the toe tip! We actually don't need it
          cmds.connectAttr("{0}.drive".format(setup_joints[i]), "{0}.bindJoint".format(drive_chain[i]))

        Foot.add_component(foot_node, ik_chain[i])
        Foot.add_component(foot_node, fk_chain[i])
        Foot.add_component(foot_node, drive_chain[i])

        # add identification attributes to these rig joints so that they may be found later in the network
        cmds.addAttr(ik_chain[i], attributeType="message", longName="ik{0}".format(joint_attr_names[i]))
        cmds.addAttr(fk_chain[i], attributeType="message", longName="fk{0}".format(joint_attr_names[i]))
        cmds.addAttr(drive_chain[i], attributeType="message", longName="drive{0}".format(joint_attr_names[i]))
        # add those same attributes to the node
        cmds.addAttr(foot_node, attributeType="message", longName="ik{0}".format(joint_attr_names[i]))
        cmds.addAttr(foot_node, attributeType="message", longName="fk{0}".format(joint_attr_names[i]))
        cmds.addAttr(foot_node, attributeType="message", longName="drive{0}".format(joint_attr_names[i])) 
        # now connect those attributes
        cmds.connectAttr("{0}.ik{1}".format(foot_node, joint_attr_names[i]), "{0}.ik{1}".format(ik_chain[i], joint_attr_names[i]))
        cmds.connectAttr("{0}.fk{1}".format(foot_node, joint_attr_names[i]), "{0}.fk{1}".format(fk_chain[i], joint_attr_names[i]))
        cmds.connectAttr("{0}.drive{1}".format(foot_node, joint_attr_names[i]), "{0}.drive{1}".format(drive_chain[i], joint_attr_names[i]))


      root_node = cmds.listConnections("{0}.root".format(cls.get_char_node(foot_node)))[0]

      cmds.group(ik_chain[0], fk_chain[0], drive_chain[0], 
                name="{0}_foot_joints_grp".format(cmds.getAttr("{0}.side".format(foot_node))),
                parent = cmds.listConnections("{0}.dntGrp".format(root_node))[0])

      cmds.select(cl=True)

  @classmethod
  def make_controls(cls, foot_node):
    """Main method to build all the controls on the foot. Requires the 3 joint chain created from make_joint_chains. 

    Args:
      foot_node (str): The foot node to build the controls on. 

    """

    cls.make_ik_foot(foot_node)
    cls.make_fk_foot(foot_node)
    cls.make_drive_foot(foot_node)

  @classmethod
  def make_ik_foot(cls, foot_node):
    """If the joint contract has been fulfilled then it will make an ik_foot component. 

    Args:
      foot_node (str): The foot node to add the setup on.
      
    """

    setup_joints = []
    for joint in ["ikFoot", "ikToe","ikToeEnd", "heelLoc", "bankInLoc", "bankOutLoc"]:
      node = cmds.listConnections("{0}.{1}".format(foot_node, joint))
      if node:
        setup_joints.append(node[0])
      else:
        om.MGlobal.displayError("Insufficient joint contract for ikFoot")
        return

    side = cmds.getAttr("{0}.side".format(foot_node))
    ik_foot = cls.get_leg_node_attr(foot_node, "ikControl")[0]
    leg_ik_handle = cls.get_leg_node_attr(foot_node, "ikHandle")[0]

    ik_foot = foot.IkFoot(foot=setup_joints[0], toe=setup_joints[1], toe_end=setup_joints[2], 
                          heel=setup_joints[3], bank_in=setup_joints[4], bank_out=setup_joints[5], 
                          side=side, 
                          ik_foot=ik_foot,
                          leg_ik_handle=leg_ik_handle)

    ik_handles = ik_foot.make_ik_handles()
    reverse_ball_joint = ik_foot.make_reverse_hierarchy()
    ik_foot.make_primary_attr()
    ik_foot.make_secondary_attr()
    # ik_foot.setup_ikfk_switch_grp()

    for comp in ik_handles + reverse_ball_joint:
      Foot.add_component(foot_node, comp)

    # make a special attribute on the foot so that we can access the ikfk switch group
    # cmds.addAttr(foot_node, longName="ikFkSwitchGroup", attributeType="message")
    # cmds.addAttr(ik_foot.ikfkswitch_grp, longName="module", attributeType="message")
    # cmds.connectAttr("{0}.ikFkSwitchGroup".format(foot_node), "{0}.module".format(ik_foot.ikfkswitch_grp))

  @classmethod
  def make_fk_foot(cls, foot_node):
    """If the joint contract has been fulfilled then it will make an fk_foot component. 

    Args:
      foot_node (str): The foot node to add the setup on.
      
    """


    setup_joints = []
    for joint in ["fkFoot", "fkToe","fkToeEnd"]:
      node = cmds.listConnections("{0}.{1}".format(foot_node, joint))
      if node:
        setup_joints.append(node[0])
      else:
        om.MGlobal.displayError("Insufficient joint contract for ikFoot")
        return

    side = cmds.getAttr("{0}.side".format(foot_node))

    fk_foot = foot.FkFoot(foot=setup_joints[0], toe=setup_joints[1], toe_end=setup_joints[2], side=side, fk_foot=cls.get_leg_node_attr(foot_node, "footFk")[0])
    toe_ctrl = fk_foot.make_control_curves()

    Foot.add_component(foot_node, toe_ctrl)

  @classmethod
  def make_drive_foot(cls, foot_node):
    """If the joint contract has been fulfilled then it will make a drive_foot component. 

    Args:
      foot_node (str): The foot node to add the setup on.
      
    """

    setup_joints = []
    for joint in ["ikFoot", "ikToe","ikToeEnd"] + ["fkFoot", "fkToe","fkToeEnd"] + ["driveFoot","driveToe","driveToeEnd"]:
      node = cmds.listConnections("{0}.{1}".format(foot_node, joint))
      if node:
        setup_joints.append(node[0])
      else:
        om.MGlobal.displayError("Insufficient joint contract for ikFoot")
        return

    ik_switch = cls.get_leg_node_attr(foot_node, "ikSwitch")[0]
    switch_rev = cmds.ls(cmds.listConnections(ik_switch), type="reverse")[0]

    foot.DriveFoot(ik_foot=setup_joints[0:3],
                   fk_foot=setup_joints[3:6],
                   drive_foot=setup_joints[6:9],
                   switch_cc=ik_switch,
                   switch_rev=switch_rev)

  @classmethod 
  def get_leg_node_attr(cls, foot_node, attr):
    """Used by methods in the class to connect the foot to its leg module parent. 
    Finds the module of the parent joint. Expects it to be a foot. 
      
    Args;
      foot_node (str): The foot node to add to.
      attr (str): The attribute on the leg module to look for. 

    """

    foot = cmds.listConnections("{0}.foot".format(foot_node))
    foot_parent = cmds.listRelatives(foot[0], parent=True)
    leg_node = cmds.listConnections("{0}.module".format(foot_parent[0]))
    return cmds.listConnections("{0}.{1}".format(leg_node[0], attr))