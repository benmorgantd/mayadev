import maya.cmds as cmds
import Gossamer.modules.module as module
reload(module)
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
import Gossamer.components.fk_leg as fk_leg
reload(fk_leg)
import Gossamer.components.ik_leg as ik_leg
reload(ik_leg)
import Gossamer.components.drive_leg as drive_leg
reload(drive_leg)


class IkFkDogLeg(module.Module):
  """A module for making ikfk leg chains. 

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
    contract (list): ["startJoint", "midJoint", "endJoint"]
    
  """

  contract = ["startJoint", "midJoint", "endJoint"]

  def __init__(self, char_node=None, node=None, name="ikFkLeg", side="lf"):
    super(IkFkDogLeg, self).__init__(char_node, node, name, side, module_type="IkFkDogLeg")

    self.make_contract(IkFkDogLeg.contract)

  @classmethod
  def set_bind_joints(cls, ikFkLeg_node, joints):
    """Designates the given joints as the bind joints for the module.
  
    Args:
      ikFkLeg_node (str): The node to add the joints to. 
      joints (list): The joints to add to the module. Should be oriented nicely. The elbow should only have one axis of orient values. 

    """

    if len(joints) != 5:
      om.MGlobal.displayError("IkFkDogLeg needs 5 joints as an input")

    existing_bindJoints = cmds.listConnections("{0}.bindJoints".format(ikFkLeg_node))
    
    if not existing_bindJoints:
      for i in range(5):
        # if the joint hasn't had its custom attributes added to it yet
        if "module" not in cmds.listAttr(joints[i]):
          cmds.addAttr(joints[i], attributeType="message", longName="module")
          cmds.addAttr(joints[i], attributeType="message", longName="ik")
          cmds.addAttr(joints[i], attributeType="message", longName="drive")
          cmds.addAttr(joints[i], attributeType="message", longName="component")

          cmds.connectAttr("{0}.bindJoints".format(ikFkLeg_node),"{0}.module".format(joints[i]))

          if i == 0:
            cmds.addAttr(joints[i], attributeType="message", longName="startJoint") 
            cmds.connectAttr("{0}.startJoint".format(ikFkLeg_node), "{0}.startJoint".format(joints[i]))
          elif i == 1:
            cmds.addAttr(joints[i], attributeType="message", longName="midJoint") 
            cmds.connectAttr("{0}.midJoint".format(ikFkLeg_node), "{0}.midJoint".format(joints[i]))
          else = 2:
            cmds.addAttr(joints[i], attributeType="message", longName="wristJoint") 
            cmds.connectAttr("{0}.endJoint".format(ikFkLeg_node), "{0}.endJoint".format(joints[i]))
        else:
          for i in range(0,3):
            if i == 0:
              try:
                cmds.connectAttr("{0}.startJoint".format(ikFkLeg_node),"{0}.startJoint".format(joints[i]))  
              except RuntimeError:
                pass
            elif i == 1:
              try:
                cmds.connectAttr("{0}.midJoint".format(ikFkLeg_node),"{0}.midJoint".format(joints[i]))
              except RuntimeError:
                pass
            elif i == 2:
              try:
                cmds.connectAttr("{0}.endJoint".format(ikFkLeg_node),"{0}.endJoint".format(joints[i]))
              except RuntimeError:
                pass
    else:
      for i in range(3):
        if i == 0:
          try:
            cmds.connectAttr("{0}.startJoint".format(ikFkLeg_node),"{0}.startJoint".format(joints[i]))  
          except RuntimeError:
            pass
        elif i == 1:
          try:
            cmds.connectAttr("{0}.midJoint".format(ikFkLeg_node),"{0}.midJoint".format(joints[i]))
          except RuntimeError:
            pass
        elif i == 2:
          try:
            cmds.connectAttr("{0}.endJoint".format(ikFkLeg_node),"{0}.endJoint".format(joints[i]))
          except RuntimeError:
            pass
  
  @classmethod
  def make_joint_chains(cls, ikFkLeg_node):
    """Makes the 3 joint ik/fk/drive chains from the module's bind joints. 

    Args:
      ikFkLeg_node (str): The ikFkLeg node to add these joint chains to. 
      * Each joint on the resulting chain will be accessible via message attribute connections on the module node. 

    """

    # cmds.undoInfo(openChunk=1)

    startJoint = cmds.listConnections("{0}.startJoint".format(ikFkLeg_node))
    midJoint = cmds.listConnections("{0}.midJoint".format(ikFkLeg_node))
    endJoint = cmds.listConnections("{0}.endJoint".format(ikFkLeg_node))

    setup_joints = [startJoint, midJoint, endJoint]


    if startJoint and midJoint and endJoint:
      cmds.select(clear=1)
      ik_chain = cmds.duplicate(startJoint, midJoint, endJoint, parentOnly=1, renameChildren=1)
      cmds.select(clear=1)
      fk_chain = cmds.duplicate(startJoint, midJoint, endJoint, parentOnly=1, renameChildren=1)
      cmds.select(clear=1)
      drive_chain = cmds.duplicate(startJoint, midJoint, endJoint, parentOnly=1, renameChildren=1)

      # rename joint chains
      for i in range(2,-1, -1):
        ik_chain[i] = cmds.rename(ik_chain[i], "{0}_{1}".format(setup_joints[i][0],"ik"))
        fk_chain[i] = cmds.rename(fk_chain[i], "{0}_{1}".format(setup_joints[i][0], "fk"))
        drive_chain[i] = cmds.rename(drive_chain[i], "{0}_{1}".format(setup_joints[i][0], "drive"))

        cmds.addAttr(ik_chain[i], attributeType="message", longName="bindJoint") 
        cmds.addAttr(ik_chain[i], attributeType="message", longName="ikJoint") 
        cmds.addAttr(fk_chain[i], attributeType="message", longName="bindJoint") 
        cmds.addAttr(fk_chain[i], attributeType="message", longName="fkJoint") 
        cmds.addAttr(drive_chain[i], attributeType="message", longName="bindJoint")
        cmds.addAttr(drive_chain[i], attributeType="message", longName="driveJoint")

        cmds.connectAttr("{0}.ik".format(setup_joints[i][0]), "{0}.bindJoint".format(ik_chain[i]))
        cmds.connectAttr("{0}.fk".format(setup_joints[i][0]), "{0}.bindJoint".format(fk_chain[i]))
        cmds.connectAttr("{0}.drive".format(setup_joints[i][0]), "{0}.bindJoint".format(drive_chain[i]))

        # cmds.connectAttr("{0}.ikJoints".format(ikFkLeg_node), "{0}.ikJoint".format(ik_chain[i]))
        # cmds.connectAttr("{0}.fkJoints".format(ikFkLeg_node), "{0}.fkJoint".format(fk_chain[i]))
        # cmds.connectAttr("{0}.driveJoints".format(ikFkLeg_node), "{0}.driveJoint".format(drive_chain[i]))

      root = cmds.listConnections("{0}.root".format(cls.get_char_node(ikFkLeg_node)))[0]
      cmds.parent(ik_chain[0], fk_chain[0], drive_chain[0], cmds.listConnections("{0}.dntGrp".format(root)))

      cmds.select(cl=1)

    else:
      om.MGlobal.displayInfo("startJoint: {0}\n# midJoint: {1}\n# endJoint: {2}".format(startJoint, midJoint, endJoint))
      om.MGlobal.displayError("Module {0} does not meet contract requirements".format(ikFkLeg_node))

    # cmds.undoInfo(closeChunk=1)

  @classmethod
  def make_ik_system(cls, ikFkLeg_node, joints):
    """If the joint contract has been fulfilled then it will make an ik_leg component. 

    Args:
      ikFkLeg_node (str): The foot node to add the setup on.
      joints (list): The ik leg chain to use to build this system. This module should exist in the state after make_joint_chains.
    
    Returns:
      leg (ik_leg.IkLeg): An IkLeg object component.

    """

    # make message attributes that will allow the node to know its ik control & pole vector
    if "ikControl" not in cmds.listAttr(ikFkLeg_node):
      cmds.addAttr(ikFkLeg_node, longName="ikControl", attributeType="message")
      cmds.addAttr(ikFkLeg_node, longName="ikPoleVectorControl", attributeType="message")
      cmds.addAttr(ikFkLeg_node, longName="ikHandle", attributeType="message")

    leg = ik_leg.IkLeg(joints=joints, ikFkLeg_node=ikFkLeg_node)

    # make a space switch for the ik leg control to follow the world vs the pelvis
    cls.setup_world_follow(control=leg.ik_cc[0], constraint_type="parent", defaultValue=1, module=ikFkLeg_node)

    return leg

  @classmethod
  def make_fk_system(cls, ikFkLeg_node, joints):
    """If the joint contract has been fulfilled then it will make an fk_leg component. 

    Args:
      ikFkLeg_node (str): The foot node to add the setup on.\n
      joints (list): The fk leg chain to use to build this system. This module should exist in the state after make_joint_chains.
    
    Returns:
      leg (fk_leg.FkLeg): An FkLeg object component.

    """

    # make message attributes that will allow the node to know its ik control & pole vector
    if "upLegFk" not in cmds.listAttr(ikFkLeg_node):
      cmds.addAttr(ikFkLeg_node, longName="upLegFk", attributeType="message")
      cmds.addAttr(ikFkLeg_node, longName="loLegFk", attributeType="message")
      cmds.addAttr(ikFkLeg_node, longName="footFk", attributeType="message")

    leg = fk_leg.FkLeg(joints=joints, ikFkLeg_node=ikFkLeg_node)

    cls.setup_world_follow(control=leg.upLeg_cc[0], constraint_type="orient", defaultValue=0, module=ikFkLeg_node)

    return leg

  @classmethod
  def make_drive_system(cls, ikFkLeg_node, joints, ik_leg, fk_leg):
    if "ikSwitch" not in cmds.listAttr(ikFkLeg_node):
      cmds.addAttr(ikFkLeg_node, longName="ikSwitch", attributeType="message")

    leg = drive_leg.DriveLeg(joints=joints, ikFkLeg_node=ikFkLeg_node, ik_leg=ik_leg, fk_leg=fk_leg)

    cmds.parentConstraint(cmds.listConnections("{0}.worldSpace".format(cls.get_char_node(ikFkLeg_node)))[0], leg.switch_cc_grp, mo=1)

    return leg

  @classmethod
  def build_controls(cls, ikFkLeg_node):
    """Runs all the preceding 'make' functions to give us the final 'rig' state of the character. \n
    Requires that the module's contract has been fulfilled. 
    
    Args:
      ikFkLeg_node (str): The ikFkLeg node to build on. 
  
    """

    # first make our three chains
    IkFkDogLeg.make_joint_chains(ikFkLeg_node)

    # IK System
    startJoint = cmds.listConnections("{0}.startJoint".format(ikFkLeg_node))
    midJoint = cmds.listConnections("{0}.midJoint".format(ikFkLeg_node))
    endJoint = cmds.listConnections("{0}.endJoint".format(ikFkLeg_node))

    if startJoint and midJoint and endJoint:
      startJoint_ik = cmds.listConnections("{0}.ik".format(startJoint[0]))
      midJoint_ik = cmds.listConnections("{0}.ik".format(midJoint[0]))
      endJoint_ik = cmds.listConnections("{0}.ik".format(endJoint[0]))
    else:
        om.MGlobal.displayError("Invalid joint contract for IkFkDogLeg module.")
        return

    if startJoint_ik and midJoint_ik and endJoint_ik:
        ik_leg = cls.make_ik_system(ikFkLeg_node, [startJoint_ik[0], midJoint_ik[0], endJoint_ik[0]])
    else:
      om.MGlobal.displayError("Missing IK joints in contract.")
      return

    # FK System

    if startJoint and midJoint and endJoint:
      startJoint_fk = cmds.listConnections("{0}.fk".format(startJoint[0]))
      midJoint_fk = cmds.listConnections("{0}.fk".format(midJoint[0]))
      endJoint_fk = cmds.listConnections("{0}.fk".format(endJoint[0]))

      if startJoint_fk and midJoint_fk and endJoint_fk:
        fk_leg = cls.make_fk_system(ikFkLeg_node, [startJoint_fk[0], midJoint_fk[0], endJoint_fk[0]])

    # BIND System

    if startJoint and midJoint and endJoint:
      startJoint_drive = cmds.listConnections("{0}.drive".format(startJoint[0]))
      midJoint_drive = cmds.listConnections("{0}.drive".format(midJoint[0]))
      endJoint_drive = cmds.listConnections("{0}.drive".format(endJoint[0]))

      if startJoint_drive and midJoint_drive and endJoint_drive:
        drive_leg = cls.make_drive_system(ikFkLeg_node=ikFkLeg_node, joints=[startJoint_drive[0], midJoint_drive[0], endJoint_drive[0]],
                              ik_leg=ik_leg, fk_leg=fk_leg)

    cls.connect_comps_to_node(cmds.listConnections("{0}.components".format(ikFkLeg_node)), ikFkLeg_node)
    cls.organize_module(ikFkLeg_node, ik_leg, fk_leg, drive_leg, startJoint)

    # cmds.undoInfo(closeChunk=True)

  @classmethod
  def organize_module(cls, ikFkLeg_node, ik_leg, fk_leg, drive_leg, startJoint):
    """Organizes the components into their respective groups and parents them into the correct places. 

    Args:
      iFkLeg_node (str): 

    """


    # finally, organize our components
    comps = cmds.group(ik_leg.ik_grp, fk_leg.upLeg_cc_grp, drive_leg.switch_cc_grp, name="{0}_comps".format(cmds.getAttr("{0}.name".format(ikFkLeg_node))))
    jnts = cmds.group(ik_leg.joints[0], fk_leg.joints[0], drive_leg.joints[0], name="{0}_joints".format(cmds.getAttr("{0}.name".format(ikFkLeg_node))))
    module = cmds.group(comps, jnts, name="{0}_module_grp".format(cmds.getAttr("{0}.name".format(ikFkLeg_node))))

    # add that module group as a component so that the ikfk leg can easily be destroyed
    IkFkDogLeg.add_component(ikFkLeg_node, module)
    IkFkDogLeg.add_component(ikFkLeg_node, comps)

    # get the character node
    char_node = cls.get_char_node(ikFkLeg_node)
    root_node = cmds.listConnections("{0}.root".format(char_node))[0]
    dnt_grp = cmds.listConnections("{0}.dntGrp".format(root_node))[0]

    cmds.parent(module, dnt_grp)

    # parent and scale constrain the module to the joint above the startJoint
    startJoint_parent = cmds.listRelatives(startJoint[0], parent=1)

    # group our ik joints to maintain proper scaling
    ik_jnt_grp = cmds.group(ik_leg.joints[0], name="{0}_grp".format(ik_leg.joints[0]))

    if startJoint_parent:
      startJoint_parent_comp = cmds.listConnections("{0}.component".format(startJoint_parent[0]))
      if startJoint_parent_comp:
        cmds.parentConstraint(startJoint_parent_comp[0], ik_jnt_grp, mo=1)

        # to get our ik to scale correctly, it needs to connect to that comp via direct connection
        cmds.connectAttr("{0}.scale".format(startJoint_parent_comp[0]), "{0}.scale".format(ik_jnt_grp))


        cmds.parent(comps, startJoint_parent_comp[0])


    IkFkDogLeg.echo_data(ikFkLeg_node)

    cmds.select(cl=1)

  # todo: make this an inherited method
  @classmethod
  def connect_comps_to_node(cls, control_list, ikFkLeg_node):
    """Connects the given controls and their shapes to the node.
  
    Args:
      control_list (list): The list of controls to connect
      ikFkLeg_node (str): The node to connect the controls to. 

    """



    if control_list:
      for comp in control_list:
        if type(comp) == list:
          comp = comp[0]

        if comp.endswith("_fk_cc"):
          cmds.addAttr(comp, attributeType="message", longName="bindJoint")
          cmds.connectAttr("{0}.component".format(comp.replace("_fk_cc","")),
                           "{0}.bindJoint".format(comp))

        # connect our color value to each of the transform node's shape nodes if it has them
        comp_shapes = cmds.listRelatives(comp, type="shape")
        if comp_shapes:
          for shape in comp_shapes:
            cmds.setAttr("{0}.overrideEnabled".format(shape), 1)
            cmds.connectAttr("{0}.color".format(ikFkLeg_node), "{0}.overrideColor".format(shape))
    else:
      om.MGlobal.displayError("Cannot connect components to node. Control list invalid.")


