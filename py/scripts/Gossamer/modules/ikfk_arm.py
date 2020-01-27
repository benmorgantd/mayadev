import maya.cmds as cmds
import Gossamer.modules.module as module
reload(module)
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
import Gossamer.components.fk_arm as fk_arm
reload(fk_arm)
import Gossamer.components.ik_arm as ik_arm
reload(ik_arm)
import Gossamer.components.drive_arm as drive_arm
reload(drive_arm)


class IkFkArm(module.Module):
  """A module for making ikfk arm chains. 

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

  def __init__(self, char_node=None, node=None, name="ikFkArm", side="lf"):
    super(IkFkArm, self).__init__(char_node, node, name, side, module_type="IkFkArm")

    self.make_contract(IkFkArm.contract)

  @classmethod
  def set_bind_joints(cls, ikFkArm_node, joints):
    """Designates the given joints as the bind joints for the module.
  
    Args:
      ikFkArm_node (str): The node to add the joints to. 
      joints (list): The joints to add to the module. Should be oriented nicely. The elbow should only have one axis of orient values. 

    """

    if len(joints) != 3:
      om.MGlobal.displayError("IkFkArm needs 3 joints as an input")

    existing_bindJoints = cmds.listConnections("{0}.bindJoints".format(ikFkArm_node))
    
    if not existing_bindJoints:
      for i in range(0, 3):
        # if the joint hasn't had its custom attributes added to it yet
        if "module" not in cmds.listAttr(joints[i]):
          cmds.addAttr(joints[i], attributeType="message", longName="module")
          cmds.addAttr(joints[i], attributeType="message", longName="ik")
          cmds.addAttr(joints[i], attributeType="message", longName="fk")
          cmds.addAttr(joints[i], attributeType="message", longName="drive")
          cmds.addAttr(joints[i], attributeType="message", longName="component")

          cmds.connectAttr("{0}.bindJoints".format(ikFkArm_node),"{0}.module".format(joints[i]))

          if i == 0:
            cmds.addAttr(joints[i], attributeType="message", longName="startJoint") 
            cmds.connectAttr("{0}.startJoint".format(ikFkArm_node), "{0}.startJoint".format(joints[i]))
          elif i == 1:
            cmds.addAttr(joints[i], attributeType="message", longName="midJoint") 
            cmds.connectAttr("{0}.midJoint".format(ikFkArm_node), "{0}.midJoint".format(joints[i]))
          else:
            cmds.addAttr(joints[i], attributeType="message", longName="endJoint") 
            cmds.connectAttr("{0}.endJoint".format(ikFkArm_node), "{0}.endJoint".format(joints[i]))
    else:
      for i in range(0,3):
        if i == 0:
          cmds.connectAttr("{0}.startJoint".format(ikFkArm_node),"{0}.startJoint".format(joints[i]), force=True)  
        elif i == 1:
          cmds.connectAttr("{0}.midJoint".format(ikFkArm_node),"{0}.midJoint".format(joints[i]), force=True)
        elif i == 2:
          cmds.connectAttr("{0}.endJoint".format(ikFkArm_node),"{0}.endJoint".format(joints[i]), force=True)
  
  @classmethod
  def make_joint_chains(cls, ikFkArm_node):
    """Makes the 3 joint ik/fk/drive chains from the module's bind joints. 

    Args:
      ikFkArm_node (str): The ikFkArm node to add these joint chains to. 
      * Each joint on the resulting chain will be accessible via message attribute connections on the module node. 

    """

    startJoint = cmds.listConnections("{0}.startJoint".format(ikFkArm_node))
    midJoint = cmds.listConnections("{0}.midJoint".format(ikFkArm_node))
    endJoint = cmds.listConnections("{0}.endJoint".format(ikFkArm_node))

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

      root = cmds.listConnections("{0}.root".format(cls.get_char_node(ikFkArm_node)))[0]
      cmds.parent(ik_chain[0], fk_chain[0], drive_chain[0], cmds.listConnections("{0}.dntGrp".format(root)))

      cmds.select(cl=1)

    else:
      om.MGlobal.displayInfo("startJoint: {0}\n# midJoint: {1}\n# endJoint: {2}".format(startJoint, midJoint, endJoint))
      om.MGlobal.displayError("Module {0} does not meet contract requirements".format(ikFkArm_node))


  @classmethod
  def make_ik_system(cls, ikFkArm_node, joints):
    """If the joint contract has been fulfilled then it will make an ik_arm component. 

    Args:
      ikFkArm_node (str): The foot node to add the setup on.
      joints (list): The ik arm chain to use to build this system. This module should exist in the state after make_joint_chains.
    
    Returns:
      arm (ik_arm.IkArm): An IkArm object component.

    """

    # make message attributes that will allow the node to know its ik control & pole vector
    if "ikControl" not in cmds.listAttr(ikFkArm_node):
      cmds.addAttr(ikFkArm_node, longName="ikControl", attributeType="message")
      cmds.addAttr(ikFkArm_node, longName="ikPoleVectorControl", attributeType="message")

    arm = ik_arm.IkArm(joints=joints, ikFkArm_node=ikFkArm_node)

    cls.setup_world_follow(control=arm.ik_cc[0], constraint_type="parent", defaultValue=1, module=ikFkArm_node)

    return arm

  @classmethod
  def make_fk_system(cls, ikFkArm_node, joints):
    """If the joint contract has been fulfilled then it will make an fk_arm component. 

    Args:
      ikFkArm_node (str): The foot node to add the setup on.\n
      joints (list): The fk arm chain to use to build this system. This module should exist in the state after make_joint_chains.
    
    Returns:
      arm (fk_arm.FkArm): An FkArm object component.

    """

    # make message attributes that will allow the node to know its ik control & pole vector
    if "upArmFk" not in cmds.listAttr(ikFkArm_node):
      cmds.addAttr(ikFkArm_node, longName="upArmFk", attributeType="message")
      cmds.addAttr(ikFkArm_node, longName="loArmFk", attributeType="message")
      cmds.addAttr(ikFkArm_node, longName="wristFk", attributeType="message")

    arm = fk_arm.FkArm(joints=joints, ikFkArm_node=ikFkArm_node)

    cls.setup_world_follow(control=arm.upArm_cc[0], constraint_type="orient", defaultValue=1, module=ikFkArm_node)

    return arm

  @classmethod
  def make_drive_system(cls, ikFkArm_node, joints, ik_arm, fk_arm):
    """If the joint contract has been fulfilled then it will make drive_arm component. 

    Args:
      ikFkArm_node (str): The foot node to add the setup on.\n
      joints (list): The drive arm chain to use to build this system. This module should exist in the state after make_joint_chains\n
      * This method should be run following the build of both the ik and fk systems. \n
      ik_arm (list): The ik_arm chain to blend with.\n
      fk_arm (list): The fk_arm chain to blend with.

    Returns:
      arm (drive_arm.DriveArm): An DriveArm object component.

    """

    if "ikSwitch" not in cmds.listAttr(ikFkArm_node):
      cmds.addAttr(ikFkArm_node, longName="ikSwitch", attributeType="message")

    arm = drive_arm.DriveArm(joints=joints, ikFkArm_node=ikFkArm_node, ik_arm=ik_arm, fk_arm=fk_arm)

    cmds.parentConstraint(cmds.listConnections("{0}.worldSpace".format(cls.get_char_node(ikFkArm_node)))[0], arm.switch_cc_grp, mo=1)

    return arm

  @classmethod
  def build_controls(cls, ikFkArm_node):
    """Runs all the preceding 'make' functions to give us the final 'rig' state of the character. \n
    Requires that the module's contract has been fulfilled. 
    
    Args:
      ikFkArm_node (str): The ikFkArm node to build on. 
  
    """

    # first make our three chains
    IkFkArm.make_joint_chains(ikFkArm_node)

    # IK System
    startJoint = cmds.listConnections("{0}.startJoint".format(ikFkArm_node))
    midJoint = cmds.listConnections("{0}.midJoint".format(ikFkArm_node))
    endJoint = cmds.listConnections("{0}.endJoint".format(ikFkArm_node))

    if startJoint and midJoint and endJoint:
      startJoint_ik = cmds.listConnections("{0}.ik".format(startJoint[0]))
      midJoint_ik = cmds.listConnections("{0}.ik".format(midJoint[0]))
      endJoint_ik = cmds.listConnections("{0}.ik".format(endJoint[0]))
    else:
        om.MGlobal.displayError("Invalid joint contract for IkFkArm module.")
        return

    if startJoint_ik and midJoint_ik and endJoint_ik:
        ik_arm = cls.make_ik_system(ikFkArm_node, [startJoint_ik[0], midJoint_ik[0], endJoint_ik[0]])
    else:
      om.MGlobal.displayError("Missing IK joints in contract.")
      return

    # FK System

    if startJoint and midJoint and endJoint:
      startJoint_fk = cmds.listConnections("{0}.fk".format(startJoint[0]))
      midJoint_fk = cmds.listConnections("{0}.fk".format(midJoint[0]))
      endJoint_fk = cmds.listConnections("{0}.fk".format(endJoint[0]))

      if startJoint_fk and midJoint_fk and endJoint_fk:
        fk_arm = cls.make_fk_system(ikFkArm_node, [startJoint_fk[0], midJoint_fk[0], endJoint_fk[0]])

    # BIND System
 
    if startJoint and midJoint and endJoint:
      startJoint_drive = cmds.listConnections("{0}.drive".format(startJoint[0]))
      midJoint_drive = cmds.listConnections("{0}.drive".format(midJoint[0]))
      endJoint_drive = cmds.listConnections("{0}.drive".format(endJoint[0]))

      if startJoint_drive and midJoint_drive and endJoint_drive:
        drive_arm = cls.make_drive_system(ikFkArm_node=ikFkArm_node, joints=[startJoint_drive[0], midJoint_drive[0], endJoint_drive[0]],
                              ik_arm=ik_arm, fk_arm=fk_arm)

    cls.connect_comps_to_node(cmds.listConnections("{0}.components".format(ikFkArm_node)), ikFkArm_node)
    cls.organize_module(ikFkArm_node, ik_arm, fk_arm, drive_arm, startJoint)

  @classmethod
  def organize_module(cls, ikFkArm_node, ik_arm, fk_arm, drive_arm, startJoint):
    """Organizes the components into their respective groups and parents them into the correct places. 

    Args:
      iFkArm_node (str): 


    """


    # finally, organize our components
    comps = cmds.group(ik_arm.ik_grp, fk_arm.upArm_cc_grp, drive_arm.switch_cc_grp, name="{0}_comps".format(cmds.getAttr("{0}.name".format(ikFkArm_node))))
    jnts = cmds.group(ik_arm.joints[0], fk_arm.joints[0], drive_arm.joints[0], name="{0}_joints".format(cmds.getAttr("{0}.name".format(ikFkArm_node))))
    module = cmds.group(comps, jnts, name="{0}_module_grp".format(cmds.getAttr("{0}.name".format(ikFkArm_node))))

    # add that module group as a component so that the ikfk arm can easily be destroyed
    IkFkArm.add_component(ikFkArm_node, module)
    IkFkArm.add_component(ikFkArm_node, comps)

    # get the character node
    char_node = cls.get_char_node(ikFkArm_node)
    root_node = cmds.listConnections("{0}.root".format(char_node))[0]
    dnt_grp = cmds.listConnections("{0}.dntGrp".format(root_node))[0]

    cmds.parent(module, dnt_grp)

    # parent and scale constrain the module to the joint above the startJoint
    startJoint_parent = cmds.listRelatives(startJoint[0], parent=1)

    # group our ik joints to maintain proper scaling
    ik_jnt_grp = cmds.group(ik_arm.joints[0], name="{0}_grp".format(ik_arm.joints[0]))

    if startJoint_parent:
      startJoint_parent_comp = cmds.listConnections("{0}.component".format(startJoint_parent[0]))
      if startJoint_parent_comp:
        cmds.parentConstraint(startJoint_parent_comp[0], ik_jnt_grp, mo=1)

        # to get our ik to scale correctly, it needs to connect to that comp via direct connection
        cmds.connectAttr("{0}.scale".format(startJoint_parent_comp[0]), "{0}.scale".format(ik_jnt_grp))

        cmds.parent(comps, startJoint_parent_comp[0])

    cmds.select(cl=1)

  @classmethod
  def connect_comps_to_node(cls, control_list, ikFkArm_node):
    """Connects the given controls and their shapes to the node.
  
    Args:
      control_list (list): The list of controls to connect
      ikFkArm_node (str): The node to connect the controls to. 

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
            # cmds.connectAttr("{0}.color".format(ikFkArm_node), "{0}.overrideColor".format(shape))
    else:
      om.MGlobal.displayError("Cannot connect components to node. Control list invalid.")

  @classmethod
  def destroy_controls(cls, ikFkArm_node):
    cmds.delete(cmds.listConnections("{0}.components".format(ikFkArm_node)))