import maya.cmds as cmds
import Gossamer.library.control_curves as control_curves
import Gossamer.library.pole_vector_finder as pole_vector_finder

# quick and dirty script for making a dog leg...


class DogLeg(object):
  contract = ["upLeg", "loLeg", "ankle", "toe", "toeEnd"]

  def __init__(self, upLeg, loLeg, ankle, toe, toeEnd, name="leg", side="LF"):
    self.upLeg = upLeg
    self.loLeg = loLeg
    self.ankle = ankle
    self.toe = toe
    self.toeEnd = toeEnd
    self.input_chain = [self.upLeg, self.loLeg, self.ankle, self.toe, self.toeEnd]
    self.name = name
    self.side = side

    self.make_chains()
    self.make_full_chain_ik()
    self.make_partial_iks()
    self.make_controls()


  def make_chains(self):
    self.reverse_chain = cmds.duplicate(self.upLeg, renameChildren=True)
    cmds.delete(self.reverse_chain[len(DogLeg.contract):])
    self.reverse_chain = self.reverse_chain[0:len(DogLeg.contract)]


    for i in range(len(self.reverse_chain) - 1, -1, -1):
      renamed_joint = cmds.rename(self.reverse_chain[i], "{0}_{1}_rev".format(self.side, DogLeg.contract[i]))
      self.reverse_chain[i] = renamed_joint

    self.ik_chain = cmds.duplicate(self.upLeg, renameChildren=True)
    cmds.delete(self.ik_chain[len(DogLeg.contract):])
    self.ik_chain = self.ik_chain[0:len(DogLeg.contract)]

    for i in range(len(self.ik_chain) - 1, -1, -1):
      renamed_joint = cmds.rename(self.ik_chain[i], "{0}_{1}_ik".format(self.side, DogLeg.contract[i]))
      self.ik_chain[i] = renamed_joint

  def make_full_chain_ik(self):
    self.full_chain_ik = cmds.ikHandle(startJoint=self.reverse_chain[0], 
                                      endEffector=self.reverse_chain[-2], 
                                      name="{0}_{1}_rpik".format(self.side, self.name),
                                      solver="ikRPsolver")


  def make_partial_iks(self):
    self.upLeg_ik = cmds.ikHandle(startJoint=self.ik_chain[0], 
                                  endEffector=self.ik_chain[2], 
                                  name="{0}_{1}_rpik".format(self.side, DogLeg.contract[0]),
                                  solver="ikRPsolver")

    self.loLeg_ik = cmds.ikHandle(startJoint=self.ik_chain[1], 
                                  endEffector=self.ik_chain[3], 
                                  name="{0}_{1}_rpik".format(self.side, DogLeg.contract[1]),
                                  solver="ikRPsolver")

    self.toe_ik = cmds.ikHandle(startJoint=self.ik_chain[-2], 
                                endEffector=self.ik_chain[-1], 
                                name="{0}_{1}_scik".format(self.side, DogLeg.contract[-2]),
                                solver="ikSCsolver")

    # parent handles into the reverse leg hierarchy
    cmds.parent(self.upLeg_ik[0], self.reverse_chain[-2])
    cmds.parent(self.loLeg_ik[0], self.reverse_chain[-3])


  def make_controls(self):
    self.leg_cc = control_curves.cube_ctrl(name="{0}_{1}_cc".format(self.side, self.name), scale=10)
    self.leg_cc_grp = cmds.group(self.leg_cc[0], name=self.leg_cc[0].replace("_cc", "_grp"))

    cmds.delete(cmds.pointConstraint(self.ik_chain[-2], self.leg_cc_grp))

    cmds.addAttr(self.leg_cc[0], ln="rotate_ankle", at="float", k=1)
    cmds.connectAttr(self.leg_cc[0] + ".rotate_ankle", self.reverse_chain[-2] + ".rz")

    cmds.parent(self.full_chain_ik[0], self.toe_ik[0], self.leg_cc[0], absolute=True)

    for i in range(len(self.input_chain) - 1):
      print self.ik_chain[i], self.input_chain[i]
      cmds.parentConstraint(self.ik_chain[i], self.input_chain[i], mo=0)


    # pole vector
    self.pv_cc = control_curves.sphere_ctrl(name="{0}_{1}_pv_cc".format(self.side, self.name), scale=5)
    self.pv_cc_grp = cmds.group(self.pv_cc[0], name=self.pv_cc[0].replace("_cc","_grp"))

    cmds.xform(self.pv_cc_grp, ws=1, t=pole_vector_finder.find_pole_vector(self.ik_chain[0], self.ik_chain[1], self.ik_chain[2], scale_factor=2))

    cmds.poleVectorConstraint(self.pv_cc[0], self.full_chain_ik[0])

    cmds.hide(self.reverse_chain[0], self.ik_chain[0], cmds.ls(type="ikHandle"))