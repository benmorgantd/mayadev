"""The skin brush settings panel: widgets bound to a SkinBrushSession (RigModules D65). Qt only, no Maya (host.py docks it).

The brush operation, the falloff (surface or volume), the radius, the strength and the through mesh switch, over the RigModules `skinBrushCtx` context. The
context is the source of truth, so a Ctrl + drag resize in the viewport shows here: the panel reads the context again
on a timer while it is showing, and writes it as the widgets change.
"""

from __future__ import annotations

import math

from PySide6 import QtCore, QtGui, QtWidgets

import bmaya.core.log
import bmaya.maya.skinbrush
from bmaya.maya_ui import host
from bmaya.maya_ui.widgets import CollapsibleSection

OBJECT_NAME = "bmayaSkinBrushPanel"
POLL_MS = 250
RADIUS_SLIDER_STEPS = 1000
RADIUS_SLIDER_MIN = 0.01     # the slider is logarithmic between these. The box takes any radius above the session's minimum
RADIUS_SLIDER_MAX = 1000.0
STRENGTH_SLIDER_STEPS = 100
DOCK_BESIDE = "Outliner"
NO_CONTEXT_TEXT = "The brush is made when you activate it or change a setting."


def radius_to_slider(radius: float) -> int:
    """The slider position of a radius: logarithmic from RADIUS_SLIDER_MIN to RADIUS_SLIDER_MAX, clamped to its ends."""
    fraction = math.log(max(radius, RADIUS_SLIDER_MIN) / RADIUS_SLIDER_MIN) / math.log(RADIUS_SLIDER_MAX / RADIUS_SLIDER_MIN)
    return round(min(max(fraction, 0.0), 1.0) * RADIUS_SLIDER_STEPS)


def slider_to_radius(position: int) -> float:
    return RADIUS_SLIDER_MIN * (RADIUS_SLIDER_MAX / RADIUS_SLIDER_MIN) ** (position / RADIUS_SLIDER_STEPS)


class SkinBrushPanel(QtWidgets.QWidget):
    """The panel's window. Reads the session's settings whenever its changed event emits, and polls the session while
    it is showing."""

    def __init__(self, session: bmaya.maya.skinbrush.SkinBrushSession, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Skin Brush")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.session = session

        layout = QtWidgets.QVBoxLayout(self)
        self.section = CollapsibleSection("Brush")
        layout.addWidget(self.section)
        layout.addStretch(1)
        form = QtWidgets.QFormLayout()
        self.section.content_layout.addLayout(form)

        self.operation_combo = QtWidgets.QComboBox()
        for name, (label, tip) in bmaya.maya.skinbrush.OPERATION_INFO.items():
            self.operation_combo.addItem(label, name)    # the context's name is the item's data
            self.operation_combo.setItemData(self.operation_combo.count() - 1, tip, QtCore.Qt.ItemDataRole.ToolTipRole)
        self.operation_combo.setToolTip("What a dab does to the weights under the brush")
        form.addRow("Operation", self.operation_combo)

        self.falloff_combo = QtWidgets.QComboBox()
        self.falloff_combo.addItems(bmaya.maya.skinbrush.FALLOFFS)
        self.falloff_combo.setToolTip("Surface: the radius is a length along the mesh, so the brush never reaches across a gap.\n"
                                      "Volume: the radius is a distance in space, so it also reaches a part of the mesh that is close but not connected.")
        form.addRow("Falloff", self.falloff_combo)

        self.radius_box = QtWidgets.QDoubleSpinBox()
        self.radius_box.setDecimals(3)
        self.radius_box.setRange(bmaya.maya.skinbrush.MIN_RADIUS, 100000.0)
        self.radius_box.setSingleStep(0.5)
        self.radius_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, RADIUS_SLIDER_STEPS)
        tip = "A length over the mesh surface, in scene units. Ctrl + drag in the viewport resizes it too."
        self.radius_box.setToolTip(tip)
        self.radius_slider.setToolTip(tip)
        form.addRow("Radius", self._row(self.radius_slider, self.radius_box))

        self.strength_box = QtWidgets.QDoubleSpinBox()
        self.strength_box.setDecimals(2)
        self.strength_box.setRange(0.01, 1.0)
        self.strength_box.setSingleStep(0.05)
        self.strength_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.strength_slider.setRange(1, STRENGTH_SLIDER_STEPS)
        tip = "How far one dab goes at the center of the brush. Holding the button still repeats the dab."
        self.strength_box.setToolTip(tip)
        self.strength_slider.setToolTip(tip)
        form.addRow("Strength", self._row(self.strength_slider, self.strength_box))

        self.smoothness_box = QtWidgets.QDoubleSpinBox()
        self.smoothness_box.setDecimals(2)
        self.smoothness_box.setRange(0.0, 1.0)
        self.smoothness_box.setSingleStep(0.05)
        self.smoothness_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.smoothness_slider.setRange(0, STRENGTH_SLIDER_STEPS)
        tip = ("Match Rest operations only. How much each vertex's change is blended with its neighbors' changes. "
               "Raise it to calm a crunchy result, at the cost of a slower fit. 0 is none.")
        self.smoothness_box.setToolTip(tip)
        self.smoothness_slider.setToolTip(tip)
        form.addRow("Smoothness", self._row(self.smoothness_slider, self.smoothness_box))

        self.through_check = QtWidgets.QCheckBox("Through mesh")
        self.through_check.setToolTip("Paint every surface the ray crosses, so the back of a mesh is painted with the front")
        self.section.content_layout.addWidget(self.through_check)

        self.activate_button = QtWidgets.QPushButton("Activate Brush")
        self.activate_button.setProperty("primary", True)
        self.activate_button.setToolTip("Make the skin brush the active tool. Select skinned meshes first.")
        self.section.content_layout.addWidget(self.activate_button)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setProperty("muted", True)
        self.status_label.setWordWrap(True)
        self.section.content_layout.addWidget(self.status_label)

        self.operation_combo.activated.connect(self._on_operation)
        self.falloff_combo.activated.connect(self._on_falloff)
        self.radius_box.editingFinished.connect(self._on_radius_box)
        self.radius_slider.valueChanged.connect(self._on_radius_slider)
        self.strength_box.editingFinished.connect(self._on_strength_box)
        self.strength_slider.valueChanged.connect(self._on_strength_slider)
        self.smoothness_box.editingFinished.connect(self._on_smoothness_box)
        self.smoothness_slider.valueChanged.connect(self._on_smoothness_slider)
        self.through_check.clicked.connect(self._on_through)
        self.activate_button.clicked.connect(self._on_activate)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self.session.refresh)
        self.session.changed.connect(self.reload)
        self.reload()

    @staticmethod
    def _row(slider: QtWidgets.QSlider, box: QtWidgets.QDoubleSpinBox) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider, 1)
        layout.addWidget(box)
        return row

    def reload(self) -> None:
        """Shows the session's settings. Setting a widget here is not the user changing it, so its signals are held."""
        settings = self.session.settings
        widgets = (self.operation_combo, self.falloff_combo, self.radius_box, self.radius_slider, self.strength_box, self.strength_slider,
                   self.smoothness_box, self.smoothness_slider, self.through_check)
        for widget in widgets:
            widget.blockSignals(True)
        if settings is not None:
            self.operation_combo.setCurrentIndex(max(self.operation_combo.findData(settings.operation), 0))
            self.falloff_combo.setCurrentText(settings.falloff)
            self.radius_box.setValue(settings.radius)
            self.radius_slider.setValue(radius_to_slider(settings.radius))
            self.strength_box.setValue(settings.strength)
            self.strength_slider.setValue(round(settings.strength * STRENGTH_SLIDER_STEPS))
            self.smoothness_box.setValue(settings.smoothness)
            self.smoothness_slider.setValue(round(settings.smoothness * STRENGTH_SLIDER_STEPS))
            # Smooth has no use for it, so it is greyed out rather than hidden, to keep the layout still.
            uses_smoothness = settings.operation != "smooth"
            self.smoothness_box.setEnabled(uses_smoothness)
            self.smoothness_slider.setEnabled(uses_smoothness)
            self.through_check.setChecked(settings.through_mesh)
        for widget in widgets:
            widget.blockSignals(False)
        if settings is None:
            self.status_label.setText(NO_CONTEXT_TEXT)
        elif self.status_label.text() == NO_CONTEXT_TEXT:
            self.status_label.setText("")   # an error shown by run() stays

    def run(self, **changes: object) -> None:
        """Writes settings to the session. An error goes to the log and the status line, never to Qt, and the widgets
        go back to what the context holds."""
        try:
            self.session.apply(**changes)
            self.status_label.setText("")
        except (ValueError, RuntimeError) as error:
            bmaya.core.log.error(str(error))
            self.status_label.setText(str(error))
            self.reload()

    def _on_operation(self, index: int) -> None:
        self.run(operation=self.operation_combo.itemData(index))

    def _on_falloff(self, index: int) -> None:
        self.run(falloff=self.falloff_combo.itemText(index))

    def _on_radius_box(self) -> None:
        self.run(radius=self.radius_box.value())

    def _on_radius_slider(self, position: int) -> None:
        self.run(radius=slider_to_radius(position))

    def _on_strength_box(self) -> None:
        self.run(strength=self.strength_box.value())

    def _on_strength_slider(self, position: int) -> None:
        self.run(strength=position / STRENGTH_SLIDER_STEPS)

    def _on_smoothness_box(self) -> None:
        self.run(smoothness=self.smoothness_box.value())

    def _on_smoothness_slider(self, position: int) -> None:
        self.run(smoothness=position / STRENGTH_SLIDER_STEPS)

    def _on_through(self, checked: bool) -> None:
        self.run(through_mesh=checked)

    def _on_activate(self) -> None:
        try:
            self.session.activate()
            self.status_label.setText("")
        except RuntimeError as error:
            bmaya.core.log.error(str(error))
            self.status_label.setText(str(error))

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """The context is read again only while the panel is showing, so a Ctrl + drag resize shows here."""
        super().showEvent(event)
        self.session.refresh()
        self.timer.start()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        super().hideEvent(event)
        self.timer.stop()


def show_window() -> QtWidgets.QWidget:
    """Opens the skin brush settings panel, docked beside the Outliner in a GUI Maya."""
    return host.show(SkinBrushPanel(bmaya.maya.skinbrush.SkinBrushSession(), parent=host.parent_window()),
                     object_name=OBJECT_NAME, dock=True, width=300, height=290, beside=DOCK_BESIDE)
