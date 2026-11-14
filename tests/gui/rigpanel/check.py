"""The active rig panel docked in a GUI Maya (RigModules D50): the checks mayapy can't make. Run by run.py through
mayalaunch.run_gui, which sets PANEL_LOG, PANEL_PLUGIN and PANEL_TEMPLATE. Writes ok / FAIL lines to the log."""
import os
import traceback

LOG = os.environ["PANEL_LOG"]
B = chr(92)


def log(message):
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(str(message) + "\n")


log("start")

import maya.cmds as cmds
import maya.utils
from PySide6 import QtCore, QtWidgets


def pump(milliseconds=400):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def build(name):
    cmds.namespace(add="skel_" + name)
    cmds.select(clear=True)
    spine1 = cmds.joint(name=":skel_%s:spine1_jnt" % name, position=(0, 10, 0))
    cmds.rigJointMarkup(spine1, usage="spine1", side="Center", export=True, skin=True)
    spine2 = cmds.joint(name=":skel_%s:spine2_jnt" % name, position=(0, 12, 0))
    cmds.rigJointMarkup(spine2, usage="spine2", side="Center", export=True, skin=True)
    joints = [spine1, spine2]
    for side, x in (("Left", 2), ("Right", -2)):
        cmds.select(spine2, replace=True)
        joint = cmds.joint(name=":skel_%s:arm_%s_jnt" % (name, side[0].lower()), position=(x, 12, 0))
        cmds.rigJointMarkup(joint, usage="arm", side=side, export=True, skin=True)
        joints.append(joint)
    cmds.createRigFromTemplate(*joints, template=os.environ["PANEL_TEMPLATE"], asset="shooter" + B + name)
    cmds.select(clear=True)


STATE = {}


def check(condition, message):
    log(("ok   " if condition else "FAIL ") + message)
    return condition


def steps():
    cmds.loadPlugin(os.environ["PANEL_PLUGIN"])
    build("hero")
    build("villain")
    import bmaya.maya.activerig
    import bmaya.maya_ui.rigpanel
    tracker = bmaya.maya.activerig.ActiveRigTracker()
    import bmaya.maya_ui.host
    name = bmaya.maya_ui.host.dock_control_name(bmaya.maya_ui.rigpanel.OBJECT_NAME)

    def listeners():
        return len(bmaya.maya.activerig.ActiveRigTracker.changed.listeners())

    base = listeners()
    log("tracker listeners before: %d" % base)

    pump(6000)   # a user opens the panel long after startup has finished laying out the windows
    panel = bmaya.maya_ui.rigpanel.show_window()
    STATE.update(name=name, base=base, listeners=listeners, panel=panel)
    maya.utils.executeDeferred(rest)   # queued after the dock's own deferred restore, as after a menu click


def rest():
    if not STATE.get("idle_passes"):
        STATE["idle_passes"] = 1
        maya.utils.executeDeferred(rest)   # one more idle pass: the dock's deferred restore has run by the next
        return
    try:
        steps_rest()
    except Exception:
        log("EXCEPTION " + traceback.format_exc())
    finally:
        log("finished")
        cmds.quit(force=True)


def steps_rest():
    import bmaya.maya.activerig
    import bmaya.maya_ui.host
    import bmaya.maya_ui.rigpanel
    name, base, listeners, panel = (STATE[key] for key in ("name", "base", "listeners", "panel"))
    pump(1500)   # the recheck in host._restore fires inside this
    check(cmds.workspaceControl(name, query=True, exists=True), "workspaceControl exists after show_window")
    check(panel.isVisible(), "panel is visible in its workspace control")
    panel.pose_section.header.click()
    check(not panel.buttons["zero"].isVisible(), "pressing the Pose title folds it")
    panel.pose_section.header.click()
    check(panel.buttons["zero"].isVisible(), "pressing it again opens it")
    check(listeners() == base + 1, "one session listens (%d)" % listeners())
    check(len(panel.group_buttons) > 0, "Select section has %d group buttons" % len(panel.group_buttons))

    panel.group_buttons[0].click()
    check(len(cmds.ls(selection=True)) > 0, "click selected %d nodes" % len(cmds.ls(selection=True)))
    panel.buttons["zero"].click()
    panel.buttons["key_rig"].click()
    check(cmds.keyframe(cmds.ls(selection=True)[0], query=True, keyframeCount=True) > 0, "Key keyed the rig")

    villain_ctrl = "villain:spine1_ctrl_c"
    cmds.select(villain_ctrl, replace=True)
    pump(200)
    check(panel.session.rig.namespace == "villain", "selecting another rig switched the panel to %s" % panel.session.rig.namespace)

    # The space section follows the selection and switches the space.
    root = cmds.ls("villain:*", type="rigRootModule")[0]
    arm = cmds.getRigControls(root, side="Left")[0]
    cmds.createRigConstraint(arm, driver=["layout.end", "spine.end"], label=["World", "Chest"])
    check(not panel.space_section.isVisible(), "no Space section while no control is selected")
    cmds.select(arm, replace=True)
    pump(300)
    check(panel.space_section.isVisible() and [b.text() for b in panel.space_buttons] == ["World", "Chest"],
          "selecting a control with a space switch shows its spaces")
    panel.space_buttons[1].click()
    pump(300)
    check(cmds.getAttr(arm + ".space") == 1 and panel.space_buttons[1].isChecked(), "pressing Chest switches the space")
    cmds.currentTime(20)
    panel.space_key.setChecked(True)
    panel.space_buttons[0].click()
    pump(300)
    check(cmds.keyframe(arm + ".space", query=True, timeChange=True) == [19.0, 20.0], "Key checked: keys frames 19 and 20")
    cmds.select(villain_ctrl, replace=True)
    pump(300)
    check(not panel.space_section.isVisible(), "selecting a control with no space switch hides the section")

    # Reopen several times: the path that crashes with dockable widgets.
    for index in range(3):
        panel = bmaya.maya_ui.rigpanel.show_window()
        pump(1200)
        check(cmds.workspaceControl(name, query=True, exists=True) and panel.isVisible(), "reopen %d shows the panel" % (index + 1))
    check(listeners() == base + 1, "after reopening, one session listens (%d)" % listeners())

    # Close the dock, then change the active rig: a destroyed panel must not be called.
    cmds.workspaceControl(name, edit=True, close=True)
    pump(800)
    cmds.deleteUI(name, control=True)
    pump(800)
    check(not cmds.workspaceControl(name, query=True, exists=True), "workspaceControl is gone after deleteUI")
    check(listeners() == base, "closed panel's session stopped listening (%d)" % listeners())
    cmds.select("hero:spine1_ctrl_c", replace=True)
    pump(200)
    cmds.select(villain_ctrl, replace=True)
    pump(200)
    log("changing the active rig after close raised nothing")

    panel = bmaya.maya_ui.rigpanel.show_window()
    pump(1200)
    check(cmds.workspaceControl(name, query=True, exists=True) and panel.isVisible(), "panel shows again after a close")
    log("tracker listeners after: %d" % listeners())


def run():
    try:
        steps()
    except Exception:
        log("EXCEPTION " + traceback.format_exc())
        log("finished")
        cmds.quit(force=True)


maya.utils.executeDeferred(run)
