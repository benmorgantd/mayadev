# space switching tool (no constraints)
# Ben Morgan

import maya.cmds as cmds
import maya.OpenMaya as om

class SpaceSwitcher(object):
  def __init__(self):
    selection = None
    # MDagPaths
    self.driver = None
    self.start_frame = 0

  def set_selection(self):
    self.start_frame = cmds.currentTime(query=True)
    selection = om.MSelectionList()
    # get the selection
    om.MGlobal.getActiveSelectionList(selection)
    if selection.length() == 1:
      # get driver DAG 
      self.driver = om.MDagPath()
      selection.getDagPath(0, self.driver)

    else:
      om.MGlobal.displayError("Select a single driver control to setup the space switch.")
      return

  def attach_targets(self):
    end_frame = cmds.currentTime(query=True)

    selection = om.MSelectionList()
    # get the selection
    om.MGlobal.getActiveSelectionList(selection)
    # get target DAGs
    targets = []

    for i in range(selection.length()):
      target_dag = om.MDagPath()
      selection.getDagPath(i, target_dag)
      targets.append(target_dag)

    key_times = list(set(cmds.keyframe(self.driver.fullPathName(), query=True,
                        time=(self.start_frame, end_frame),
                        timeChange=True)))
    if not key_times:
      om.MGlobal.displayError("Driver object has no keys in selected range.")
      return

    # create an anim layer here

    # first key all at their start position
    for target in targets:
      cmds.setKeyframe(target.fullPathName(), time=self.start_frame)
