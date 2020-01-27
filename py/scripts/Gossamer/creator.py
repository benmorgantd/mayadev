# creator for Reyda 

import time
import maya.OpenMaya as om
import maya.cmds as cmds

import Gossamer.modules.character as character
reload(character)
import Gossamer.modules.module as module
reload(module)
import Gossamer.modules.root as root
reload(root)
import Gossamer.modules.single_joint as single_joint
reload(single_joint)
import Gossamer.modules.fk_chain as fk_chain
reload(fk_chain)
import Gossamer.modules.ikfk_arm as ikfk_arm
reload(ikfk_arm)
import Gossamer.modules.ikfk_leg as ikfk_leg
reload(ikfk_leg)
import Gossamer.modules.foot as foot
reload(foot)
import Gossamer.modules.twist as twist
reload(twist)
import Gossamer.library.ctrl_cv_data as ctrl_cv_data
reload(ctrl_cv_data)
import Gossamer.modules.finger as finger
reload(finger)
import Gossamer.modules.ribbon as ribbon
reload(ribbon)
import Gossamer.modules.scik as scik
reload(scik)
import Gossamer.modules.spline_ik as spline_ik
reload(spline_ik)
import Gossamer.modules.fk_hierarchy as fk_hierarchy
reload(fk_hierarchy)
import Gossamer.modules.ikChain as ikChain
reload(ikChain)

class Creator(object):
  """Holds the logic for the assembly of character modules. Subclasses of this object extend its build_character function
  by calling the necessary "make" functions. 

  Args:
    char_name (str): The name to use for our character.

  """

  def __init__(self, char_name="Reyda", charnode=None):
    self.char_name = char_name
    self.charnode = charnode

    self.build_character()

    for oc in cmds.ls("*orientConstraint*", type="constraint"):
      cmds.setAttr(oc + ".interpType", 2)
    for pc in cmds.ls("*parentConstraint*", type="constraint"):
      cmds.setAttr(pc + ".interpType", 2)

  def build_character(self):
    return None

  def make_CharNode(self):
    if self.charnode:
      character.Character(self.char_name, node=self.charnode)
    else:
      self.charnode = character.Character(self.char_name, node=None)
      
    module.Module.echo_data("{0}_CharNode".format(self.char_name))

    return self.charnode

  def make_Root(self):
    # create a root
    myRoot = root.Root(char_node="{0}_CharNode".format(self.char_name), side="c")
    root.Root.build_controls(myRoot.node)
    root.Root.echo_data(myRoot.node)

    return myRoot

  def make_SingleJoint(self, joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow", child_of=False, constrained_to=False):
    comp = single_joint.SingleJoint(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, control_shape=control_shape)
    single_joint.SingleJoint.set_bind_joints(comp.node, jnt=joint)
    single_joint.SingleJoint.build_controls(comp.node, child_of, constrained_to)
    single_joint.SingleJoint.echo_data(comp.node)

    return comp

  def make_FkChain(self, joints=[], module_name="Chain", side="LF", child_of=False, constrained_to=False, control_shape="Cube"):
    comp = fk_chain.FkChain(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, control_shape=control_shape)
    comp.set_bind_joints(comp.node, joints)
    fk_chain.FkChain.build_controls(comp.node, child_of, constrained_to)
    fk_chain.FkChain.echo_data(comp.node)

    return comp

  def make_IkFkLeg(self, joints=[], module_name="Leg", side="LF"):
    leg = ikfk_leg.IkFkLeg(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side)
    ikfk_leg.IkFkLeg.set_bind_joints(leg.node, joints)
    ikfk_leg.IkFkLeg.build_controls(leg.node)

    return leg

  def make_Foot(self, joints=[], locs=[], module_name="Foot", side="LF"):
    foot_module = foot.Foot(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side)
    foot.Foot.set_bind_joints(foot_module.node, joints)
    foot.Foot.set_foot_locators(foot_module.node, locs)
    foot.Foot.make_joint_chains(foot_module.node)
    foot.Foot.make_controls(foot_module.node)

    foot.Foot.echo_data(foot_module.node)

    return foot_module

  def make_IkFkArm(self, joints=[], module_name="Arm", side="LF"):
    arm = ikfk_arm.IkFkArm(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side)
    ikfk_arm.IkFkArm.set_bind_joints(arm.node, joints)
    ikfk_arm.IkFkArm.build_controls(arm.node)
    ikfk_arm.IkFkArm.echo_data(arm.node)

    return arm

  def make_QuatTwist(self, module_name="Twist", side="LF", extract_joint="Wrist", twist_joints=[], axis="X", multiplier=1, limb_module=None):
    twist_node = twist.Twist(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side)
    twist_node.set_bind_joint(extract_joint, twist_node.node)
    twist_node.build_twist(twist_node.node, extraction_type="quaternion", axis=axis)
    twist.Twist.connect_to_twist_joints(twist_joints, twist_node.node, axis=axis, multiplier=multiplier, limb_module=limb_module)
    twist.Twist.echo_data(twist_node.node)

    return twist_node

  def make_IkTwist(self, module_name="Twist", side="LF", extract_joint="Shoulder", start_joint="Elbow", twist_joints=[], ik_parent=None, limb_module=None):
    twist_node = twist.Twist(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side)
    twist_node.set_bind_joint(extract_joint, twist_node.node)
    twist_node.build_twist(twist_node.node, extraction_type="scik", start_joint=start_joint, ik_parent=ik_parent, twist_joint_parent=extract_joint)
    twist.Twist.connect_to_twist_joints(twist_joints, twist_node.node, limb_module=limb_module)
    twist.Twist.echo_data(twist_node.node)

    return twist_node

  def make_Finger(self, joints=[], module_name="Finger", side="LF", child_of=False, constrained_to=False):
    comp = finger.Finger(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side)
    comp.set_bind_joints(comp.node, joints)
    finger.Finger.build_controls(comp.node, child_of, constrained_to)
    finger.Finger.echo_data(comp.node)

    return comp

  def make_Ribbon(self, module_name="Strap", name_prefix="strap", side=None, joint_parent="chest", custom_joints=None, custom_plane=None, num_bind_joints=7, num_control_joints=4):
    if not joint_parent:
      return

    myRibbon = ribbon.Ribbon(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, joint_parent=joint_parent)
    ribbon.Ribbon.build_nurbs_plane(myRibbon.node, custom_plane)
    ribbon.Ribbon.build_drive_joints(myRibbon.node, name_prefix="{0}_drive".format(name_prefix), num_bind_joints=num_bind_joints)
    ribbon.Ribbon.build_control_joints(myRibbon.node, name_prefix=name_prefix, num_control_joints=num_control_joints)
    ribbon.Ribbon.build_bind_joints(myRibbon.node, custom_joints=custom_joints, name_prefix=name_prefix)
    ribbon.Ribbon.change_joint_shapes(myRibbon.node)
    ribbon.Ribbon.echo_data(myRibbon.node)

    return myRibbon

  def make_ScIk(self, joint="sword", module_name="Sword", side="LF", control_shape="Cylinder",child_of=False, constrained_to=False, down_vector=[-1,0,0]):
    comp = scik.ScIk(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, control_shape=control_shape)
    scik.ScIk.set_bind_joints(comp.node, jnt=joint)
    scik.ScIk.build_controls(comp.node, child_of, constrained_to, down_vector=down_vector)
    scik.ScIk.echo_data(comp.node)

    return comp

  def make_SplineIK(self, joints=[], module_name="Chain", side="LF", stretchy=False, num_controls=3, control_shape="Cube"):
    comp = spline_ik.SplineIK(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, control_shape=control_shape)
    spline_ik.SplineIK.set_bind_joints(comp.node, joints=joints)
    spline_ik.SplineIK.build_controls(comp.node, stretchy=stretchy, num_controls=num_controls)
    spline_ik.SplineIK.echo_data(comp.node)

    return comp


  def make_FkHierarchy(self, startJoint=None, module_name="fkHierarchy", stop_at=[], side="LF", control_shape="Cube"):
    comp = fk_hierarchy.FkHierarchy(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, control_shape=control_shape)
    fk_hierarchy.FkHierarchy.set_bind_joints(comp.node, start_joint=startJoint, stop_at=stop_at)
    fk_hierarchy.FkHierarchy.build_controls(comp.node, stop_at=stop_at)
    fk_hierarchy.FkHierarchy.echo_data(comp.node)

    return comp

  def make_IkChain(self, startJoint=None, endJoint=None, module_name="fkHierarchy", joints=[], side="LF", control_shape="Cube", sol="ikSpringSolver"):
    comp = ikChain.IkChain(char_node="{0}_CharNode".format(self.char_name), name=module_name, side=side, control_shape=control_shape)
    ikChain.IkChain.set_bind_joints(comp.node, startJoint=startJoint, endJoint=endJoint)
    ikChain.IkChain.build_controls(comp.node, sol=sol, joints=joints)
    ikChain.IkChain.echo_data(comp.node)

    return comp

  def connect_bind_joints(self):
    character.Character.connect_bind_joints(self.charnode.node)