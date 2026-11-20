"""Maya as the host of Qt windows: the main window to parent to, showing a window once or docked, and deferring a
call. With menus.py, this is the only Maya UI code in bmaya.maya_ui (RigModules design/mayadev-ui.md, D49). Outside
Maya every function still works: there is no parent, a docked window is a plain one, and a deferred call runs from the
event loop.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtWidgets

from bmaya.maya_ui import theme

RESTORE_RECHECK_MS = 300


def parent_window() -> QtWidgets.QWidget | None:
    """Maya's main window, to parent a tool to so it stays above Maya's. None outside a GUI Maya."""
    try:
        import maya.OpenMayaUI as omui
        import shiboken6
    except ImportError:
        return None
    pointer = omui.MQtUtil.mainWindow()  # None or 0 in mayapy, which has no main window
    return shiboken6.wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None


def defer(function: Callable[[], None]) -> None:
    """Calls function once Maya is idle, so a menu item that starts it has left the stack first."""
    try:
        import maya.utils
    except ImportError:
        QtCore.QTimer.singleShot(0, function)
        return
    maya.utils.executeDeferred(function)


def find(object_name: str) -> QtWidgets.QWidget | None:
    """The open top-level widget with this object name."""
    application = QtWidgets.QApplication.instance()
    if application is None:
        return None
    for widget in application.topLevelWidgets():
        if widget.objectName() == object_name and widget.isVisible():
            return widget
    return None


def show(widget: QtWidgets.QWidget, *, object_name: str, dock: bool = False,
         width: int = 385, height: int = 735, beside: str = "AttributeEditor") -> QtWidgets.QWidget:
    """Shows a window, once: an open window with the same object name is closed first. When that window refuses to
    close (unsaved edits the user kept), it is raised instead and widget is discarded. Returns the window on screen.

    dock puts the widget in a Maya workspace control tabbed with the one named beside (the Attribute Editor by
    default, and also when beside is not open). Outside Maya it is a plain window.
    """
    existing = find(object_name)
    if existing is not None and not existing.close():
        widget.deleteLater()
        existing.raise_()
        existing.activateWindow()
        return existing
    widget.setObjectName(object_name)
    theme.apply(widget)
    if dock and _dock(widget, object_name, width, height, beside):
        return widget
    widget.show()
    return widget


def dock_control_name(object_name: str) -> str:
    """The name of the workspace control that docks the window with this object name."""
    return object_name + "WorkspaceControl"


def _dock(widget: QtWidgets.QWidget, name: str, width: int, height: int, beside: str = "AttributeEditor") -> bool:
    """Puts widget in a workspace control for the window called name. False outside a GUI Maya."""
    try:
        import maya.cmds as cmds
        import maya.OpenMayaUI as omui
        import shiboken6
    except ImportError:
        return False
    if not hasattr(cmds, "workspaceControl") or not omui.MQtUtil.mainWindow():
        return False
    # The control needs a name of its own: Maya refuses one that another object already has, and the widget in it
    # has the window's object name.
    control_name = dock_control_name(name)
    if cmds.workspaceControl(control_name, query=True, exists=True):
        cmds.workspaceControl(control_name, edit=True, close=True)
        cmds.deleteUI(control_name, control=True)
    if not cmds.workspaceControl(beside, query=True, exists=True):
        beside = "AttributeEditor"
    control = cmds.workspaceControl(
        control_name, tabToControl=[beside, -1], initialWidth=width, minimumWidth=True, initialHeight=height,
        widthProperty="preferred", label=widget.windowTitle() or name)
    container = shiboken6.wrapInstance(int(omui.MQtUtil.findControl(control)), QtWidgets.QWidget)
    container.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)   # as the older, working dock code did
    if container.layout() is None:
        QtWidgets.QVBoxLayout(container)
    container.layout().addWidget(widget)
    defer(lambda: _restore(control))
    return True


def _restore(control: str) -> None:
    """Shows a docked control. The first restore can run before Maya has finished laying the new tab out and leave
    it hidden (reproduced in a GUI Maya 2026, tests/gui/rigpanel), so it looks again once the event loop has run."""
    import maya.cmds as cmds
    import maya.OpenMayaUI as omui
    import shiboken6

    def is_hidden() -> bool:
        pointer = omui.MQtUtil.findControl(control)
        return bool(pointer) and not shiboken6.wrapInstance(int(pointer), QtWidgets.QWidget).isVisible()

    if cmds.workspaceControl(control, query=True, exists=True):
        cmds.workspaceControl(control, edit=True, restore=True)
        QtCore.QTimer.singleShot(RESTORE_RECHECK_MS, lambda: is_hidden() and cmds.workspaceControl(control, edit=True, restore=True))
