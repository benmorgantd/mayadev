"""The Asset Editor window: the asset you work on, and tabs for its files, markup and shapes (RigModules
design/asset-editor.md, D61).

A docked window like the active rig panel and the library browser. A header holds the asset picker, the skeleton, rig
and look, and a New menu. Below it a tab per job. Every button is one call on the AssetEditorSession, which holds the
state and does the work; a failure goes to the log, where every tool's errors go, and to the status line. Closing the
window closes the session, which removes its callbacks and clears the asset. Qt only, no Maya (host.py docks it).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

import bmaya.core.log
import bmaya.maya.asseteditor
from bmaya.maya_ui import host
from bmaya.maya_ui.assetwidgets import AssetPicker, FileStatusTable, OwnerCombo
from bmaya.maya_ui.librarybrowser import menu_action

OBJECT_NAME = "bmayaAssetEditor"
FILES_TAB = "Files"
TAB_OPTION = "bmayaAssetEditorTab"


class AssetEditor(QtWidgets.QWidget):
    """The window. Reads the session's asset_ids, context, files and header text whenever its changed event emits."""

    def __init__(self, session: bmaya.maya.asseteditor.AssetEditorSession,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asset Editor")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.session = session
        # A docked window is destroyed with its workspace control, often without a closeEvent. Its session then
        # removes its callbacks, or the next scene change would call a deleted widget.
        self.destroyed.connect(session.close)
        self.new_actions: dict[str, QtGui.QAction] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(self._build_header())
        self.mismatch_bar = QtWidgets.QFrame()
        mismatch_layout = QtWidgets.QHBoxLayout(self.mismatch_bar)
        mismatch_layout.setContentsMargins(4, 2, 4, 2)
        self.mismatch_label = QtWidgets.QLabel()
        self.mismatch_label.setWordWrap(True)
        self.switch_button = QtWidgets.QPushButton("Switch")
        self.switch_button.setToolTip("Work on the active rig's asset")
        self.switch_button.clicked.connect(lambda: self.run(self.session.use_active_rig))
        mismatch_layout.addWidget(self.mismatch_label, 1)
        mismatch_layout.addWidget(self.switch_button)
        layout.addWidget(self.mismatch_bar)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_files_tab(), FILES_TAB)
        layout.addWidget(self.tabs, 1)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.session.changed.connect(self.reload)
        self.reload()

    # ---- building --------------------------------------------------------------------------

    def _build_header(self) -> QtWidgets.QLayout:
        header = QtWidgets.QVBoxLayout()
        top = QtWidgets.QHBoxLayout()
        self.picker = AssetPicker()
        self.picker.asset_picked.connect(lambda asset_id: self.run(lambda: self.session.set_asset(asset_id)))
        top.addWidget(self.picker, 1)
        self.use_rig_button = QtWidgets.QPushButton("Use Active Rig")
        self.use_rig_button.setToolTip("Work on the asset of the active rig")
        self.use_rig_button.clicked.connect(lambda: self.run(self.session.use_active_rig))
        top.addWidget(self.use_rig_button)
        self.new_button = QtWidgets.QToolButton()
        self.new_button.setText("New")
        self.new_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.new_menu = QtWidgets.QMenu(self.new_button)
        for key, text, command in (("project", "Project...", self.session.create_project),
                                   ("asset", "Asset...", self.session.create_asset),
                                   ("rig", "Rig...", self.session.create_rig),
                                   ("look", "Look...", self.session.create_look)):
            action = menu_action(self.new_menu, text)
            action.triggered.connect(lambda checked=False, command=command: self.run(command))
            self.new_actions[key] = action
        self.new_button.setMenu(self.new_menu)
        top.addWidget(self.new_button)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setToolTip("Read the asset list, the files and the scene again")
        self.refresh_button.clicked.connect(lambda: self.run(self.session.refresh))
        top.addWidget(self.refresh_button)
        header.addLayout(top)

        owners = QtWidgets.QHBoxLayout()
        self.skeleton_combo, self.rig_combo, self.look_combo = OwnerCombo(), OwnerCombo(), OwnerCombo()
        for label, combo, set_owner in (("Skeleton", self.skeleton_combo, self.session.context.set_skeleton),
                                        ("Rig", self.rig_combo, self.session.context.set_rig),
                                        ("Look", self.look_combo, self.session.context.set_look)):
            owners.addWidget(QtWidgets.QLabel(label))
            owners.addWidget(combo, 1)
            combo.owner_picked.connect(lambda name, set_owner=set_owner: self.run(lambda: set_owner(name)))
        header.addLayout(owners)
        return header

    def _build_files_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.files_table = FileStatusTable()
        self.files_table.save_requested.connect(lambda key: self.run(lambda: self._save(key)))
        self.files_table.load_requested.connect(lambda key: self.run(lambda: self.session.files.load(key)))
        layout.addWidget(self.files_table, 1)
        self.files_message = QtWidgets.QLabel()
        self.files_message.setWordWrap(True)
        layout.addWidget(self.files_message)
        row = QtWidgets.QHBoxLayout()
        self.build_button = QtWidgets.QPushButton("Build Rig")
        self.build_button.setToolTip("Build the chosen rig in the scene, wearing the chosen look")
        self.build_button.clicked.connect(lambda: self.run(self.session.files.build_rig))
        row.addWidget(self.build_button)
        row.addStretch(1)
        layout.addLayout(row)
        return tab

    # ---- reading the session ---------------------------------------------------------------

    def run(self, command: Callable[[], object]) -> None:
        """Runs a session command. An error goes to the log and the status line, and never reaches Qt."""
        self.status_label.setText("")
        try:
            command()
        except (RuntimeError, ValueError, OSError) as error:   # AssetError, PromptError and AssetIdError are among them
            bmaya.core.log.error(str(error))
            self.status_label.setText(str(error))

    def _save(self, key: str) -> None:
        path = self.session.files.save(key)
        if path:
            self.status_label.setText(f"Saved {path}")

    def reload(self) -> None:
        """Shows the session's asset, owners, mismatch strip and files."""
        session, context = self.session, self.session.context
        self.picker.set_ids(session.asset_ids, context.asset_id)
        self.skeleton_combo.set_names(context.skeletons(), context.skeleton, "none saved")
        self.rig_combo.set_names(context.rigs(), context.rig, "none")
        self.look_combo.set_names(context.looks(), context.look, "none")
        mismatch = session.rig_mismatch()
        self.mismatch_bar.setVisible(bool(mismatch))
        self.mismatch_label.setText(mismatch)
        self.use_rig_button.setEnabled(session.active_rig() is not None)
        files = session.files
        self.files_table.set_rows(files.rows)
        self.files_message.setText(files.message)
        self.files_message.setVisible(bool(files.message))
        self.build_button.setEnabled(bool(files.rows) and context.rig is not None)

    # ---- window events ---------------------------------------------------------------------

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """The session reads the selection only while the window is showing, and the files are read again on show,
        since the scene may have changed while it was hidden."""
        super().showEvent(event)
        self.session.watch_selection(True)
        self.session.files.refresh()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        super().hideEvent(event)
        self.session.watch_selection(False)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Closing the window ends the session: its callbacks go and the asset is cleared."""
        self.session.close()
        super().closeEvent(event)


def show_window() -> QtWidgets.QWidget:
    """Opens the Asset Editor, docked beside the Attribute Editor in a GUI Maya."""
    return host.show(AssetEditor(bmaya.maya.asseteditor.AssetEditorSession(), parent=host.parent_window()),
                     object_name=OBJECT_NAME, dock=True)
