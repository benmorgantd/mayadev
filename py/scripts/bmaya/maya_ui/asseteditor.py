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
import bmaya.maya.markupmodel
import bmaya.maya.shapemodel
from bmaya.core.fieldset import FieldState
from bmaya.maya_ui import host, theme
from bmaya.maya_ui.assetwidgets import AssetPicker, FileStatusTable, MixedFieldForm, OwnerCombo
from bmaya.maya_ui.widgets import ListModel, menu_action

OBJECT_NAME = "bmayaAssetEditor"
FILES_TAB = "Files"
MARKUP_TAB = "Markup"
SHAPES_TAB = "Shapes"
CONTROL_COLUMNS = ("Control", "Module", "Side", "Usage", "Mirror")


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
        self.markup_tab = self._build_markup_tab()
        self.tabs.addTab(self.markup_tab, MARKUP_TAB)
        self.shapes_tab = self._build_shapes_tab()
        self.tabs.addTab(self.shapes_tab, SHAPES_TAB)
        self.tabs.currentChanged.connect(lambda index: self._sync_active())
        layout.addWidget(self.tabs, 1)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.session.changed.connect(self.reload)
        self.session.markup.changed.connect(self.reload_markup)
        self.session.shapes.changed.connect(self.reload_shapes)
        self.reload()
        self.reload_markup()
        self.reload_shapes()

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
        self.files_table.restore_requested.connect(lambda key: self.run(lambda: self._restore(key)))
        self.files_table.load_by_name_requested.connect(lambda key: self.run(lambda: self.session.files.load_by_name(key)))
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

    def _build_markup_tab(self) -> QtWidgets.QWidget:
        """The selected joints' markup, edited across all of them, and the selected controls' markup, shown."""
        markup = bmaya.maya.markupmodel
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.markup_summary = QtWidgets.QLabel()
        layout.addWidget(self.markup_summary)

        self.markup_form = MixedFieldForm(markup.JOINT_FIELDS)
        self.markup_form.field_edited.connect(
            lambda name, value: self.run(lambda: self.session.markup.set_field(name, value)))
        layout.addWidget(self.markup_form)
        row = QtWidgets.QHBoxLayout()
        self.remove_markup_button = QtWidgets.QPushButton("Remove Markup")
        self.remove_markup_button.setToolTip("Remove the markup of the selected joints")
        self.remove_markup_button.clicked.connect(lambda: self.run(self.session.markup.remove))
        self.mirror_joints_button = QtWidgets.QPushButton("Mirror Joints")
        self.mirror_joints_button.setToolTip("Mirror the selected _L_JNT joints onto _R_JNT joints")
        self.mirror_joints_button.clicked.connect(lambda: self.run(self.session.markup.mirror_joints))
        self.twist_button = QtWidgets.QPushButton("Add Twist Joints...")
        self.twist_button.setToolTip("Select the start joint, then the end joint")
        self.twist_button.clicked.connect(lambda: self.run(self.session.markup.add_twist_joints))
        for button in (self.remove_markup_button, self.mirror_joints_button, self.twist_button):
            row.addWidget(button)
        layout.addLayout(row)

        self.add_box = QtWidgets.QGroupBox("Joints without markup")
        add_layout = QtWidgets.QVBoxLayout(self.add_box)
        self.add_form = MixedFieldForm(markup.JOINT_FIELDS)
        self.add_form.set_states({"usage": FieldState("", False, 1), "side": FieldState("Center", False, 1),
                                  "export": FieldState(True, False, 1), "skin": FieldState(True, False, 1)})
        add_layout.addWidget(self.add_form)
        self.number_check = QtWidgets.QCheckBox("Number them")
        self.number_check.setToolTip("Name the usages usage_00, usage_01 and so on, in selection order. "
                                     "Two joints may not share a side and usage.")
        add_layout.addWidget(self.number_check)
        self.add_markup_button = QtWidgets.QPushButton("Add Markup")
        self.add_markup_button.clicked.connect(lambda: self.run(self._add_markup))
        add_layout.addWidget(self.add_markup_button)
        layout.addWidget(self.add_box)

        self.markup_warnings = QtWidgets.QLabel()
        self.markup_warnings.setWordWrap(True)
        layout.addWidget(self.markup_warnings)
        self.controls_table = QtWidgets.QTableView()
        self.controls_model = ListModel(
            {}, columns=[(CONTROL_COLUMNS[0], lambda control: control.node.rsplit("|", 1)[-1]),
                         (CONTROL_COLUMNS[1], lambda control: control.module.rsplit("|", 1)[-1]),
                         (CONTROL_COLUMNS[2], lambda control: control.side),
                         (CONTROL_COLUMNS[3], lambda control: control.usage),
                         (CONTROL_COLUMNS[4], lambda control: (control.mirror or "").rsplit("|", 1)[-1])],
            parent=self.controls_table)
        self.controls_table.setModel(self.controls_model)
        self.controls_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.controls_table.verticalHeader().setVisible(False)
        self.controls_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.controls_table, 1)
        return tab

    def _build_shapes_tab(self) -> QtWidgets.QWidget:
        """The selected controls' shapes, edited across all of them."""
        shapes = bmaya.maya.shapemodel
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.shapes_summary = QtWidgets.QLabel()
        layout.addWidget(self.shapes_summary)

        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addWidget(QtWidgets.QLabel("Edit"))
        self.shape_mode_combo = QtWidgets.QComboBox()
        self.shape_mode_combo.addItem("Set", shapes.SET)
        self.shape_mode_combo.addItem("Adjust", shapes.ADJUST)
        self.shape_mode_combo.setToolTip("Set: every selected control gets the value. Adjust: each control's own value "
                                         "changes by it. Translate, rotate and alpha add it, and scale multiplies by it.")
        mode_row.addWidget(self.shape_mode_combo, 1)
        layout.addLayout(mode_row)

        self.appearance_form = MixedFieldForm(shapes.APPEARANCE_FIELDS)
        self.transform_form = MixedFieldForm(shapes.TRANSFORM_FIELDS)
        for form in (self.appearance_form, self.transform_form):
            form.field_edited.connect(self._edit_shape)
            layout.addWidget(form)

        row = QtWidgets.QHBoxLayout()
        self.mirror_buttons: dict[str, QtWidgets.QPushButton] = {}
        for key, text, left_to_right in (("left_to_right", "Mirror L>R", True), ("right_to_left", "Mirror R>L", False)):
            button = QtWidgets.QPushButton(text)
            button.setIcon(theme.icon("mirror"))
            button.setToolTip("Copy the shapes of one side of the rig onto the other, in world space")
            button.clicked.connect(lambda checked=False, left_to_right=left_to_right:
                                   self.run(lambda: self.session.shapes.mirror(left_to_right, self.session.files.rig_root)))
            row.addWidget(button)
            self.mirror_buttons[key] = button
        self.save_shapes_button = QtWidgets.QPushButton("Save Shapes")
        self.save_shapes_button.setToolTip("Save the rig's control shapes to the asset")
        self.save_shapes_button.clicked.connect(lambda: self.run(lambda: self._save("shapes")))
        self.load_shapes_button = QtWidgets.QPushButton("Load Shapes")
        self.load_shapes_button.setToolTip("Load the rig's control shapes from the asset")
        self.load_shapes_button.clicked.connect(lambda: self.run(lambda: self.session.files.load("shapes")))
        row.addWidget(self.save_shapes_button)
        row.addWidget(self.load_shapes_button)
        layout.addLayout(row)
        layout.addStretch(1)
        return tab

    def _edit_shape(self, name: str, value: object) -> None:
        mode = self.shape_mode_combo.currentData()
        self.run(lambda: self.session.shapes.set_field(name, value, mode))

    def _add_markup(self) -> None:
        values = self.add_form.values()
        self.session.markup.add_markup(values["usage"] or "", values["side"] or "Center", bool(values["export"]),
                                       bool(values["skin"]), numbered=self.number_check.isChecked())

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

    def _restore(self, key: str) -> None:
        path = self.session.files.restore(key)
        if path:
            self.status_label.setText(f"Restored {path}")

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
        self.reload_shapes()   # Save Shapes and Load Shapes follow the files

    def reload_markup(self) -> None:
        """Shows the markup model: the selected joints' fields, the add box, the warnings and the controls."""
        markup = self.session.markup
        self.markup_summary.setText(markup.summary)
        self.markup_form.set_options("usage", markup.usages)
        self.add_form.set_options("usage", markup.usages)
        self.markup_form.set_states(markup.fields)
        self.markup_form.setEnabled(bool(markup.marked))
        self.remove_markup_button.setEnabled(bool(markup.marked))
        self.mirror_joints_button.setEnabled(bool(markup.joints))
        self.add_box.setVisible(bool(markup.unmarked))
        self.add_markup_button.setText(f"Add Markup to {len(markup.unmarked)} Joint(s)")
        self.number_check.setEnabled(len(markup.unmarked) > 1)
        if len(markup.unmarked) <= 1:
            self.number_check.setChecked(False)
        self.markup_warnings.setText("\n".join(markup.warnings))
        self.markup_warnings.setVisible(bool(markup.warnings))
        self.controls_model.set_items(markup.controls)
        self.controls_table.setVisible(bool(markup.controls))

    def reload_shapes(self) -> None:
        """Shows the shape model: the selected controls' fields."""
        shapes = self.session.shapes
        self.shapes_summary.setText(shapes.summary)
        self.appearance_form.set_options("shapeType", shapes.enum_names)
        self.appearance_form.set_states(shapes.fields)
        self.transform_form.set_states(shapes.fields)
        has_controls = bool(shapes.controls)
        self.appearance_form.setEnabled(has_controls)
        self.transform_form.setEnabled(has_controls)
        row = next((row for row in self.session.files.rows if row.key == "shapes"), None)
        for button, blocked, default in ((self.save_shapes_button, row.save_blocked if row else "No asset.",
                                          "Save the rig's control shapes to the asset"),
                                         (self.load_shapes_button, row.load_blocked if row else "No asset.",
                                          "Load the rig's control shapes from the asset")):
            button.setEnabled(not blocked)
            button.setToolTip(blocked or default)

    def _sync_active(self) -> None:
        """The markup and shape models read the scene only while their tab is showing."""
        showing = self.isVisible()
        self.session.markup.set_active(showing and self.tabs.currentWidget() is self.markup_tab)
        self.session.shapes.set_active(showing and self.tabs.currentWidget() is self.shapes_tab)

    # ---- window events ---------------------------------------------------------------------

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """The session reads the selection only while the window is showing, and the files are read again on show,
        since the scene may have changed while it was hidden."""
        super().showEvent(event)
        self.session.watch_selection(True)
        self.session.files.refresh()
        self._sync_active()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        super().hideEvent(event)
        self.session.watch_selection(False)
        self.session.markup.set_active(False)
        self.session.shapes.set_active(False)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Closing the window ends the session: its callbacks go and the asset is cleared."""
        self.session.close()
        super().closeEvent(event)


def show_window() -> QtWidgets.QWidget:
    """Opens the Asset Editor, docked beside the Attribute Editor in a GUI Maya."""
    return host.show(AssetEditor(bmaya.maya.asseteditor.AssetEditorSession(), parent=host.parent_window()),
                     object_name=OBJECT_NAME, dock=True)
