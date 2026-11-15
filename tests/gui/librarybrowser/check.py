"""The library browser docked in a GUI Maya (RigModules D51): the checks mayapy can't make. Run by run.py through
mayalaunch.run_gui, which sets LIBRARY_LOG, LIBRARY_PLUGIN and LIBRARY_TEMPLATE. Writes ok / FAIL lines to the log."""
import os
import traceback

LOG = os.environ["LIBRARY_LOG"]
B = chr(92)
ASSET = "shooter" + B + "hero"


def log(message):
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(str(message) + "\n")


log("start")

import maya.cmds as cmds
import maya.utils
from PySide6 import QtCore


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
    cmds.createRigFromTemplate(*joints, template=os.environ["LIBRARY_TEMPLATE"], asset="shooter" + B + name)
    cmds.select(clear=True)


STATE = {}


def check(condition, message):
    log(("ok   " if condition else "FAIL ") + message)
    return condition


def steps():
    cmds.loadPlugin(os.environ["LIBRARY_PLUGIN"])
    import bmaya.core.asset
    import bmaya.maya.activerig
    import bmaya.maya_ui.host
    import bmaya.maya_ui.librarybrowser

    root = os.environ["RIGGING_PROJECT_DIR"]
    bmaya.core.asset.Project.create(os.path.join(root, "shooter"))
    bmaya.core.asset.Asset.create(ASSET, "Character")
    build("hero")
    bmaya.maya.activerig.ActiveRigTracker()
    name = bmaya.maya_ui.host.dock_control_name(bmaya.maya_ui.librarybrowser.OBJECT_NAME)

    def listeners():
        return len(bmaya.maya.activerig.ActiveRigTracker.changed.listeners())

    base = listeners()
    log("tracker listeners before: %d" % base)
    pump(6000)   # a user opens the window long after startup has finished laying out the windows
    window = bmaya.maya_ui.librarybrowser.show_window()
    STATE.update(name=name, base=base, listeners=listeners, window=window)
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
    import bmaya.maya_ui.host
    import bmaya.maya_ui.librarybrowser
    name, base, listeners, window = (STATE[key] for key in ("name", "base", "listeners", "window"))
    import shiboken6
    pump(1500)   # the recheck in host._restore fires inside this
    check(cmds.workspaceControl(name, query=True, exists=True), "workspaceControl exists after show_window")
    # A menu action made by menu.addAction(text) was found deleted here, in a GUI Maya only (offscreen mayapy kept it).
    check(shiboken6.isValid(window.delete_mask_action) and shiboken6.isValid(window.save_mask_action), "the Masks menu's actions are alive")
    check(window.isVisible(), "window is visible in its workspace control")
    check(listeners() == base + 1, "one session listens (%d)" % listeners())
    check(window.rig_label.text() == ASSET, "the window shows the active rig's asset (%s)" % window.rig_label.text())
    check(window.table.model().rowCount() == 0, "the library starts empty")
    check(window.name_edit.text() == "pose_001", "the name is prefilled (%s)" % window.name_edit.text())

    root = cmds.ls("hero:*", type="rigRootModule")[0]
    arm = cmds.getRigControls(root, side="Left")[0]
    cmds.setAttr(arm + ".rotateY", 20)
    cmds.select(arm, replace=True)
    pump(200)
    window.tags_edit.setText("arm, wave")
    window.name_edit.returnPressed.emit()
    pump(300)
    check(window.table.model().rowCount() == 1, "Enter in the name field saved a pose")
    check(window.status_label.text() == "Saved pose_001.", "status says it saved (%s)" % window.status_label.text())
    check(window.session.selected is not None and window.session.selected.name == "pose_001", "the new pose is selected")
    check("1 controls" in window.summary_label.text(), "the details describe the selection (%s)" % window.summary_label.text())

    cmds.setAttr(arm + ".rotateY", 3)
    window.apply_button.click()
    pump(300)
    check(abs(cmds.getAttr(arm + ".rotateY") - 20) < 1e-6, "Apply put the pose back (%s)" % cmds.getAttr(arm + ".rotateY"))
    cmds.undo()
    check(abs(cmds.getAttr(arm + ".rotateY") - 3) < 1e-6, "one undo restored the scene")

    window.search_edit.setText("tag:nothing")
    pump(200)
    check(window.table.model().rowCount() == 0, "a search that matches nothing lists nothing")
    window.search_edit.setText("tag:wave")
    pump(200)
    check(window.table.model().rowCount() == 1, "tag:wave finds the pose")
    window.search_edit.setText("")

    window.kind_tabs.setCurrentIndex(1)
    pump(300)
    check(window.start_edit.isVisible() and window.table.model().rowCount() == 0, "the Animations tab shows Start at and no files")
    window.kind_tabs.setCurrentIndex(0)
    pump(300)

    # Reopen several times: the path that crashes with dockable widgets.
    for index in range(3):
        window = bmaya.maya_ui.librarybrowser.show_window()
        pump(1200)
        check(cmds.workspaceControl(name, query=True, exists=True) and window.isVisible(), "reopen %d shows the window" % (index + 1))
    check(listeners() == base + 1, "after reopening, one session listens (%d)" % listeners())
    check(window.table.model().rowCount() == 1, "the reopened window lists the saved pose")

    # Close the dock, then change the active rig: a destroyed window must not be called.
    cmds.workspaceControl(name, edit=True, close=True)
    pump(800)
    cmds.deleteUI(name, control=True)
    pump(800)
    check(not cmds.workspaceControl(name, query=True, exists=True), "workspaceControl is gone after deleteUI")
    check(listeners() == base, "closed window's session stopped listening (%d)" % listeners())
    cmds.select(arm, replace=True)
    pump(200)
    log("changing the active rig after close raised nothing")


def run():
    try:
        steps()
    except Exception:
        log("EXCEPTION " + traceback.format_exc())
        log("finished")
        cmds.quit(force=True)


maya.utils.executeDeferred(run)
