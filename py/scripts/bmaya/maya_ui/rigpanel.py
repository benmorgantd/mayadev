"""The active rig panel: widgets bound to a RigPanelSession (RigModules design/active-rig-panel.md, D50).

The panel is a launcher and a state display. Every button is one call on the session, and a click in the tree
selects in Maya, one way: the tree does not follow the viewport selection. Qt only, no Maya (host.py docks it).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

import bmaya.core.log
import bmaya.maya.rigpanel
from bmaya.maya_ui import host

OBJECT_NAME = "bmayaRigPanel"
ITEM_ROLE = QtCore.Qt.ItemDataRole.UserRole
EMPTY_TEXT = "There is no RigModules rig in the scene."


def leaf_name(name: str) -> str:
    """A node name without its namespace and path."""
    return name.rsplit("|", 1)[-1].rsplit(":", 1)[-1]


class RigPanel(QtWidgets.QWidget):
    """The panel's window. Reads the session's rigs, rig and groups whenever its changed event emits."""

    def __init__(self, session: bmaya.maya.rigpanel.RigPanelSession, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Active Rig")
        self.session = session
        self.buttons: dict[str, QtWidgets.QPushButton] = {}

        layout = QtWidgets.QVBoxLayout(self)

        header = QtWidgets.QHBoxLayout()
        self.rig_label = QtWidgets.QLabel()
        self.rig_combo = QtWidgets.QComboBox()
        refresh = self._button("refresh", "Refresh", self.session.refresh, "Read the scene's rigs again")
        header.addWidget(self.rig_label, 1)
        header.addWidget(self.rig_combo, 1)
        header.addWidget(refresh)
        layout.addLayout(header)

        self.empty_label = QtWidgets.QLabel(EMPTY_TEXT)
        layout.addWidget(self.empty_label)

        self.filter = QtWidgets.QLineEdit()
        self.filter.setPlaceholderText("Filter controls")
        self.filter.setClearButtonEnabled(True)
        layout.addWidget(self.filter)

        self.model = QtGui.QStandardItemModel(self)
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setRecursiveFilteringEnabled(True)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setHeaderHidden(True)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tree, 1)

        select_row = QtWidgets.QHBoxLayout()
        select_row.addWidget(self._button("select_all", "All", self.session.select_all, "Select every control of the rig"))
        select_row.addWidget(self._button("select_mirrors", "Mirror", self.session.select_mirrors,
                                          "Select the controls on the other side of the selected ones"))
        layout.addLayout(select_row)

        pose = QtWidgets.QGridLayout()
        commands = (
            ("zero", "Zero", self.session.zero, "Set the selected controls, or the whole rig, to rest"),
            ("mirror_left_to_right", "Mirror L>R", lambda: self.session.mirror(True), "Copy the left pose to the right"),
            ("mirror_right_to_left", "Mirror R>L", lambda: self.session.mirror(False), "Copy the right pose to the left"),
            ("flip", "Flip", self.session.flip, "Swap the pose with the other side"),
            ("key_rig", "Key", self.session.key_rig, "Key every control of the rig"),
            ("key_modules", "Key Module", self.session.key_modules, "Key the modules of the selected controls"),
        )
        for index, (name, text, command, tip) in enumerate(commands):
            pose.addWidget(self._button(name, text, command, tip), index // 3, index % 3)
        layout.addLayout(pose)

        self.filter.textChanged.connect(self.proxy.setFilterFixedString)
        self.tree.clicked.connect(self._on_clicked)
        self.rig_combo.currentIndexChanged.connect(self._on_rig_picked)
        self.session.changed.connect(self.reload)
        self.reload()

    def _button(self, name: str, text: str, command: Callable[[], None], tip: str) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
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
        """Fills the rig picker and the tree from the session."""
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

        self.model.clear()
        for group in session.groups:
            parent = QtGui.QStandardItem(f"{leaf_name(group.module)}  {group.side}  ({group.module_type})")
            parent.setData(group, ITEM_ROLE)
            for control in group.controls:
                child = QtGui.QStandardItem(leaf_name(control))
                child.setData(control, ITEM_ROLE)
                parent.appendRow(child)
            self.model.appendRow(parent)
        self.tree.expandAll()

        has_rig = session.rig is not None
        self.empty_label.setVisible(not has_rig)
        for widget in (self.filter, self.tree, *self.buttons.values()):
            widget.setEnabled(has_rig or widget is self.buttons["refresh"])

    def _on_clicked(self, index: QtCore.QModelIndex) -> None:
        """A click selects the group's or the control's nodes in Maya, and a ctrl-click adds them."""
        item = index.data(ITEM_ROLE)
        add = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)
        if isinstance(item, bmaya.maya.rigpanel.ControlGroup):
            self.run(lambda: self.session.select_group(item, add))
        elif isinstance(item, str):
            self.run(lambda: self.session.select_controls([item], add))

    def _on_rig_picked(self, index: int) -> None:
        rig_root = self.rig_combo.itemData(index)
        if rig_root:
            self.run(lambda: self.session.set_active(rig_root))


def show_window() -> QtWidgets.QWidget:
    """Opens the active rig panel, docked beside the Attribute Editor in a GUI Maya."""
    return host.show(RigPanel(bmaya.maya.rigpanel.RigPanelSession(), parent=host.parent_window()),
                     object_name=OBJECT_NAME, dock=True)
