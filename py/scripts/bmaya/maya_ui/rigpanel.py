"""The active rig panel: widgets bound to a RigPanelSession (RigModules design/active-rig-panel.md, D50).

The panel is a launcher and a state display, in folding sections: Rig, Select, Pose, and Space when the one selected
control has a space switch. Every button is one call on the session. It doesn't list controls: Maya's Outliner does
that, so the Select section has one button per module and side instead. Qt only, no Maya (host.py docks it).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

import bmaya.core.log
import bmaya.maya.rigpanel
from bmaya.maya_ui import host, theme
from bmaya.maya_ui.widgets import CollapsibleSection

OBJECT_NAME = "bmayaRigPanel"
EMPTY_TEXT = "There is no RigModules rig in the scene."
GROUP_COLUMNS = 3
ADD_MODIFIERS = QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier


def leaf_name(name: str) -> str:
    """A node name without its namespace and path."""
    return name.rsplit("|", 1)[-1].rsplit(":", 1)[-1]


def group_labels(groups: list[bmaya.maya.rigpanel.ControlGroup]) -> list[str]:
    """A button label for each group: its module's name, plus its side when two groups share the module name."""
    names = [leaf_name(group.module) for group in groups]
    return [f"{name} {group.side}" if names.count(name) > 1 else name for name, group in zip(names, groups)]


class RigPanel(QtWidgets.QWidget):
    """The panel's window. Reads the session's rigs, rig and groups whenever its changed event emits."""

    def __init__(self, session: bmaya.maya.rigpanel.RigPanelSession, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Active Rig")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.session = session
        # A docked panel is destroyed with its workspace control, often without a closeEvent. Its session then stops
        # following the tracker, or the next active rig change would call a deleted widget.
        self.destroyed.connect(session.close)
        self.buttons: dict[str, QtWidgets.QPushButton] = {}
        self.group_buttons: list[QtWidgets.QPushButton] = []

        layout = QtWidgets.QVBoxLayout(self)
        self.rig_section = CollapsibleSection("Rig")
        self.select_section = CollapsibleSection("Select")
        self.pose_section = CollapsibleSection("Pose")
        self.space_section = CollapsibleSection("Space")
        for section in (self.rig_section, self.select_section, self.pose_section, self.space_section):
            layout.addWidget(section)
        layout.addStretch(1)

        header = QtWidgets.QHBoxLayout()
        self.rig_label = QtWidgets.QLabel()
        self.rig_combo = QtWidgets.QComboBox()
        header.addWidget(self.rig_label, 1)
        header.addWidget(self.rig_combo, 1)
        header.addWidget(self._button("refresh", "Refresh", self.session.refresh, "Read the scene's rigs again"))
        self.rig_section.content_layout.addLayout(header)
        self.empty_label = QtWidgets.QLabel(EMPTY_TEXT)
        self.rig_section.content_layout.addWidget(self.empty_label)

        select_row = QtWidgets.QHBoxLayout()
        select_row.addWidget(self._button("select_all", "All", self.session.select_all, "Select every control of the rig"))
        select_row.addWidget(self._button("select_mirrors", "Mirror", self.session.select_mirrors,
                                          "Select the controls on the other side of the selected ones", "mirror"))
        self.select_section.content_layout.addLayout(select_row)
        self.groups_layout = QtWidgets.QGridLayout()
        self.select_section.content_layout.addLayout(self.groups_layout)

        pose = QtWidgets.QGridLayout()
        commands = (
            ("zero", "Zero", self.session.zero, "Set the selected controls, or the whole rig, to rest", ""),
            ("mirror_left_to_right", "Mirror L>R", lambda: self.session.mirror(True), "Copy the left pose to the right", "mirror"),
            ("mirror_right_to_left", "Mirror R>L", lambda: self.session.mirror(False), "Copy the right pose to the left", "mirror"),
            ("flip", "Flip", self.session.flip, "Swap the pose with the other side", "mirror"),
            ("key_rig", "Key", self.session.key_rig, "Key every control of the rig", "key"),
            ("key_modules", "Key Module", self.session.key_modules, "Key the modules of the selected controls", "module"),
        )
        for index, (name, text, command, tip, icon) in enumerate(commands):
            pose.addWidget(self._button(name, text, command, tip, icon), index // 3, index % 3)
        self.pose_section.content_layout.addLayout(pose)

        self.space_label = QtWidgets.QLabel()
        self.space_layout = QtWidgets.QGridLayout()
        self.space_key = QtWidgets.QCheckBox("Key")
        self.space_key.setToolTip("Key the control on the previous frame and on this one, so the animation holds "
                                  "the old space up to the switch")
        self.space_section.content_layout.addWidget(self.space_label)
        self.space_section.content_layout.addLayout(self.space_layout)
        self.space_section.content_layout.addWidget(self.space_key)
        self.space_buttons: list[QtWidgets.QPushButton] = []

        self.rig_combo.currentIndexChanged.connect(self._on_rig_picked)
        self.session.changed.connect(self.reload)
        self.session.spaces_changed.connect(self.reload_space)
        self.reload()
        self.reload_space()

    def _button(self, name: str, text: str, command: Callable[[], None], tip: str,
                icon: str = "") -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        if icon:
            button.setIcon(theme.icon(icon))
        button.setToolTip(tip)
        button.clicked.connect(lambda checked=False: self.run(command))
        self.buttons[name] = button
        return button

    def run(self, command: Callable[[], None]) -> None:
        """Runs a session command. An error from Maya goes to the log, where every tool's errors go, and never
        reaches Qt."""
        try:
            command()
        except RuntimeError as error:
            bmaya.core.log.error(str(error))

    def reload(self) -> None:
        """Fills the rig picker and the group buttons from the session."""
        session = self.session
        self.rig_combo.blockSignals(True)   # filling it is not the user picking a rig
        self.rig_combo.clear()
        for rig in session.rigs:
            self.rig_combo.addItem(f"{rig.namespace}  ({rig.variant})", rig.rig_root)
        if session.rig is not None:
            self.rig_combo.setCurrentIndex(self.rig_combo.findData(session.rig.rig_root))
        self.rig_combo.blockSignals(False)
        many = len(session.rigs) > 1
        self.rig_combo.setVisible(many)
        self.rig_label.setVisible(not many)
        self.rig_label.setText(f"{session.rig.namespace}  ({session.rig.variant})" if session.rig else "")

        for button in self.group_buttons:
            self.groups_layout.removeWidget(button)
            button.deleteLater()
        self.group_buttons = []
        for index, (group, label) in enumerate(zip(session.groups, group_labels(session.groups))):
            button = QtWidgets.QPushButton(label)
            button.setIcon(theme.icon("module"))
            button.setToolTip(f"{group.module_type}, {group.side}, {len(group.controls)} control(s). "
                              "Ctrl or Shift adds to the selection.")
            button.clicked.connect(lambda checked=False, group=group: self._on_group_clicked(group))
            self.groups_layout.addWidget(button, index // GROUP_COLUMNS, index % GROUP_COLUMNS)
            self.group_buttons.append(button)

        has_rig = session.rig is not None
        self.empty_label.setVisible(not has_rig)
        self.select_section.body.setEnabled(has_rig)
        self.pose_section.body.setEnabled(has_rig)

    def reload_space(self) -> None:
        """Shows the Space section for the selected control's space switch, or hides it when there is none."""
        for button in self.space_buttons:
            self.space_layout.removeWidget(button)
            button.deleteLater()
        self.space_buttons = []
        space = self.session.space
        self.space_section.setVisible(space is not None)
        if space is None:
            return
        self.space_label.setText(leaf_name(space.control))
        for index, label in enumerate(space.labels):
            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            button.setChecked(index == space.current)
            button.clicked.connect(lambda checked=False, label=label: self._on_space_clicked(label))
            self.space_layout.addWidget(button, index // GROUP_COLUMNS, index % GROUP_COLUMNS)
            self.space_buttons.append(button)

    def _on_space_clicked(self, label: str) -> None:
        self.run(lambda: self.session.set_space(label, key=self.space_key.isChecked()))
        self.reload_space()   # a refused switch puts the checked button back on the current space

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """The session reads the selected control's space only while the panel is showing."""
        super().showEvent(event)
        self.session.watch_selection(True)

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        super().hideEvent(event)
        self.session.watch_selection(False)

    def _on_group_clicked(self, group: bmaya.maya.rigpanel.ControlGroup) -> None:
        """Selects the group's controls in Maya. Ctrl or Shift adds them to the selection."""
        add = bool(QtWidgets.QApplication.keyboardModifiers() & ADD_MODIFIERS)
        self.run(lambda: self.session.select_group(group, add))

    def _on_rig_picked(self, index: int) -> None:
        rig_root = self.rig_combo.itemData(index)
        if rig_root:
            self.run(lambda: self.session.set_active(rig_root))


def show_window() -> QtWidgets.QWidget:
    """Opens the active rig panel, docked beside the Attribute Editor in a GUI Maya."""
    return host.show(RigPanel(bmaya.maya.rigpanel.RigPanelSession(), parent=host.parent_window()),
                     object_name=OBJECT_NAME, dock=True)
