"""The dark theme every bmaya window shares: one palette, one Qt style sheet and the few icons the sheet needs. Qt only,
no Maya. It is modelled on Visual Studio Code's Dark+: neutral greys, a single blue accent, flat controls, and a
chevron for every fold and drop-down.

apply(widget) styles a window and everything in it, so a window calls it once on its top-level widget (host.show does
that for every window it shows, and the dialog classes do it themselves). A widget that must look different sets a
property the sheet reads, instead of a style sheet of its own:

    button.setProperty("primary", True)    # the accent-coloured button of a dialog or a panel
    label.setProperty("muted", True)       # secondary text
    label.setProperty("error", True)       # a problem
    label.setProperty("warning", True)     # something to know that doesn't stop the work
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import string
import tempfile

from PySide6 import QtCore, QtGui, QtWidgets


@dataclasses.dataclass(frozen=True)
class Palette:
    """Every colour of the theme, as a #rrggbb string. The sheet and the icons read nothing else."""

    window: str = "#1f1f1f"        # the background of a window or panel
    raised: str = "#252526"        # a section's body: a step above the window
    header: str = "#2d2d30"        # a section's title bar
    header_hover: str = "#37373d"
    input: str = "#313131"         # the field of a line edit, spin box, drop-down or list
    border: str = "#3c3c3c"
    border_strong: str = "#5a5a5a"  # the edge of a check box or an unfocused control that must be seen
    text: str = "#cccccc"
    text_muted: str = "#8b8b8b"
    text_disabled: str = "#5e5e5e"
    button: str = "#3a3d41"
    button_hover: str = "#45494e"
    button_pressed: str = "#2a2d2e"
    accent: str = "#0078d4"
    accent_hover: str = "#1a8ae0"
    accent_pressed: str = "#005a9e"
    accent_text: str = "#ffffff"
    selection: str = "#04395e"     # a selected row: the accent, darkened to sit behind text
    row_hover: str = "#2a2d2e"
    error: str = "#f48771"
    warning: str = "#cca700"


DARK = Palette()

FONT_SIZE_PT = 9
RADIUS = 3

# Qt's QSS has no variables, so the palette is substituted into this with string.Template ($name).
_SHEET = string.Template("""
QWidget
{
    color: $text;
    selection-background-color: $selection;
    selection-color: $accent_text;
}

QWidget:disabled
{
    color: $text_disabled;
}

QMainWindow, QDialog, QMessageBox
{
    background: $window;
}

QMainWindow > QWidget, QDialog > QWidget
{
    background: transparent;
}

QLabel
{
    background: transparent;
}

QLabel[muted="true"]
{
    color: $text_muted;
}

QLabel[error="true"]
{
    color: $error;
}

QLabel[warning="true"]
{
    color: $warning;
}

QToolTip
{
    background: $header;
    color: $text;
    border: 1px solid $border_strong;
    padding: 3px 5px;
}

/* ---- buttons ---- */

QPushButton, QToolButton
{
    background: $button;
    color: $text;
    border: 1px solid transparent;
    border-radius: ${radius}px;
    padding: 4px 12px;
    min-height: 18px;
}

QPushButton:hover, QToolButton:hover
{
    background: $button_hover;
}

QPushButton:pressed, QToolButton:pressed
{
    background: $button_pressed;
}

QPushButton:disabled, QToolButton:disabled
{
    background: $raised;
    color: $text_disabled;
}

QPushButton:checked, QPushButton[primary="true"], QPushButton:default
{
    background: $accent;
    color: $accent_text;
}

QPushButton:checked:hover, QPushButton[primary="true"]:hover, QPushButton:default:hover
{
    background: $accent_hover;
}

QPushButton:checked:pressed, QPushButton[primary="true"]:pressed, QPushButton:default:pressed
{
    background: $accent_pressed;
}

QPushButton:checked:disabled, QPushButton[primary="true"]:disabled
{
    background: $raised;
    color: $text_disabled;
}

QToolButton
{
    background: transparent;
    padding: 3px;
}

/* ---- sections (bmaya.maya_ui.widgets.CollapsibleSection) ---- */

QFrame#collapsibleSection
{
    background: $raised;
    border: 1px solid $border;
    border-radius: ${radius}px;
}

QFrame#collapsibleSection QWidget#collapsibleBody
{
    background: transparent;
}

QPushButton#sectionHeader
{
    background: $header;
    color: $text;
    border: none;
    border-radius: ${radius}px;
    text-align: left;
    padding: 5px 8px;
    font-weight: bold;
}

QPushButton#sectionHeader:hover
{
    background: $header_hover;
}

QPushButton#sectionHeader:checked, QPushButton#sectionHeader:pressed
{
    background: $header;
    color: $text;
}

QPushButton#sectionHeader:checked:hover
{
    background: $header_hover;
}

/* ---- text fields ---- */

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox
{
    background: $input;
    color: $text;
    border: 1px solid $border;
    border-radius: ${radius}px;
    padding: 3px 6px;
    min-height: 18px;
}

QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover
{
    border-color: $border_strong;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QComboBox:on
{
    border-color: $accent;
}

QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QComboBox:disabled
{
    background: $raised;
    border-color: $border;
}

QLineEdit[error="true"]
{
    border-color: $error;
}

QComboBox::drop-down
{
    border: none;
    width: 20px;
}

QComboBox::down-arrow
{
    image: url($icon_chevron_down);
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView
{
    background: $input;
    border: 1px solid $border_strong;
    outline: none;
    selection-background-color: $selection;
}

QSpinBox::up-button, QDoubleSpinBox::up-button
{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    border: none;
    background: transparent;
}

QSpinBox::down-button, QDoubleSpinBox::down-button
{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    border: none;
    background: transparent;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::down-button:hover
{
    background: $button_hover;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow
{
    image: url($icon_chevron_up);
    width: 8px;
    height: 8px;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow
{
    image: url($icon_chevron_down);
    width: 8px;
    height: 8px;
}

/* ---- check boxes and radio buttons ---- */

QCheckBox, QRadioButton
{
    background: transparent;
    spacing: 7px;
}

QCheckBox::indicator, QRadioButton::indicator
{
    width: 14px;
    height: 14px;
    background: $input;
    border: 1px solid $border_strong;
}

QCheckBox::indicator
{
    border-radius: ${radius}px;
}

QRadioButton::indicator
{
    border-radius: 8px;
}

QCheckBox::indicator:hover, QRadioButton::indicator:hover
{
    border-color: $accent;
}

QCheckBox::indicator:checked
{
    background: $accent;
    border-color: $accent;
    image: url($icon_check);
}

QRadioButton::indicator:checked
{
    background: $accent;
    border-color: $accent;
    image: url($icon_dot);
}

QCheckBox::indicator:disabled, QRadioButton::indicator:disabled
{
    background: $raised;
    border-color: $border;
}

/* ---- lists, trees, tables ---- */

QListView, QTreeView, QTableView, QListWidget, QTreeWidget, QTableWidget
{
    background: $raised;
    alternate-background-color: $window;
    border: 1px solid $border;
    border-radius: ${radius}px;
    outline: none;
}

QListView::item, QTreeView::item, QTableView::item
{
    padding: 2px 4px;
    border: none;
}

QListView::item:hover, QTreeView::item:hover, QTableView::item:hover
{
    background: $row_hover;
}

QListView::item:selected, QTreeView::item:selected, QTableView::item:selected
{
    background: $selection;
    color: $accent_text;
}

QTreeView::branch:has-children:closed
{
    image: url($icon_chevron_right);
}

QTreeView::branch:has-children:open
{
    image: url($icon_chevron_down);
}

QHeaderView::section
{
    background: $header;
    color: $text;
    border: none;
    border-right: 1px solid $border;
    padding: 4px 6px;
}

/* ---- group boxes, tabs, splitters ---- */

QGroupBox
{
    background: transparent;
    border: 1px solid $border;
    border-radius: ${radius}px;
    margin-top: 10px;
    padding-top: 6px;
}

QGroupBox::title
{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: $text_muted;
}

QTabWidget::pane
{
    border: 1px solid $border;
    background: $raised;
}

QTabBar::tab
{
    background: $window;
    color: $text_muted;
    padding: 5px 12px;
    border: none;
    border-top: 2px solid transparent;
}

QTabBar::tab:hover
{
    color: $text;
}

QTabBar::tab:selected
{
    background: $raised;
    color: $text;
    border-top: 2px solid $accent;
}

QSplitter::handle
{
    background: $border;
}

/* ---- menus ---- */

QMenu
{
    background: $header;
    border: 1px solid $border_strong;
    padding: 4px 0;
}

QMenu::item
{
    padding: 4px 24px;
}

QMenu::item:selected
{
    background: $accent;
    color: $accent_text;
}

QMenu::separator
{
    height: 1px;
    background: $border;
    margin: 4px 0;
}

/* ---- scroll bars and progress ---- */

QScrollBar:vertical
{
    background: transparent;
    width: 12px;
    margin: 0;
}

QScrollBar:horizontal
{
    background: transparent;
    height: 12px;
    margin: 0;
}

QScrollBar::handle
{
    background: $button;
    border-radius: 4px;
    min-height: 24px;
    min-width: 24px;
    margin: 2px;
}

QScrollBar::handle:hover
{
    background: $button_hover;
}

QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page
{
    background: none;
    border: none;
    width: 0;
    height: 0;
}

QProgressBar
{
    background: $input;
    border: none;
    border-radius: ${radius}px;
    text-align: center;
    min-height: 14px;
}

QProgressBar::chunk
{
    background: $accent;
    border-radius: ${radius}px;
}
""")


def _draw(path: pathlib.Path, size: int, scale: int, color: str, painter_fn) -> None:
    image = QtGui.QImage(size * scale, size * scale, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    image.setDevicePixelRatio(scale)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    qcolor = QtGui.QColor(color)
    pen = QtGui.QPen(qcolor, 1.6)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter_fn(painter, size, qcolor)
    painter.end()
    image.save(str(path))


def _strokes(*lines: tuple[tuple[float, float], ...]):
    """A painter function that strokes each polyline given, in a 16 x 16 grid. A closed shape repeats its first
    point at the end."""
    def draw(painter: QtGui.QPainter, size: int, color: QtGui.QColor) -> None:
        k = size / 16
        for points in lines:
            painter.drawPolyline([QtCore.QPointF(x * k, y * k) for x, y in points])
    return draw


def _polyline(*points: tuple[float, float]):
    """A painter function that strokes one polyline."""
    return _strokes(points)


def _rotate(painter: QtGui.QPainter, size: int, color: QtGui.QColor) -> None:
    """Three quarters of a circle that ends in an arrowhead, open at the top right."""
    k = size / 16
    painter.drawArc(QtCore.QRectF(3 * k, 3 * k, 10 * k, 10 * k), 90 * 16, 270 * 16)
    _strokes(((11, 7.5), (13, 5.5), (15, 7.5)))(painter, size, color)


def _dot(painter: QtGui.QPainter, size: int, color: QtGui.QColor) -> None:
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QtCore.QPointF(size / 2, size / 2), size * 0.22, size * 0.22)


# icon name -> (colour field of the palette, painter function). The shapes are in a 16 x 16 grid.
_ICONS = {
    "chevron_down": ("text", _polyline((3.5, 6), (8, 10.5), (12.5, 6))),
    "chevron_right": ("text", _polyline((6, 3.5), (10.5, 8), (6, 12.5))),
    "chevron_up": ("text", _polyline((3.5, 10), (8, 5.5), (12.5, 10))),
    "check": ("accent_text", _polyline((3.5, 8.5), (6.5, 11.5), (12.5, 4.5))),
    "dot": ("accent_text", _dot),
    "plus": ("text", _strokes(((8, 3), (8, 13)), ((3, 8), (13, 8)))),
    "minus": ("text", _polyline((3, 8), (13, 8))),
    # two triangles facing each other across the centre line
    "mirror": ("text", _strokes(((8, 2), (8, 14)), ((6, 4.5), (6, 11.5), (2, 8), (6, 4.5)),
                                ((10, 4.5), (10, 11.5), (14, 8), (10, 4.5)))),
    "rotate": ("text", _rotate),
    # a diagonal with an arrowhead at each end
    "scale": ("text", _strokes(((3.5, 12.5), (12.5, 3.5)), ((3.5, 8.5), (3.5, 12.5), (7.5, 12.5)),
                               ((8.5, 3.5), (12.5, 3.5), (12.5, 7.5)))),
    # a cross with four arrowheads
    "translate": ("text", _strokes(((8, 2), (8, 14)), ((2, 8), (14, 8)), ((6, 4), (8, 2), (10, 4)),
                                   ((6, 12), (8, 14), (10, 12)), ((4, 6), (2, 8), (4, 10)),
                                   ((12, 6), (14, 8), (12, 10)))),
    # a keyframe: the diamond of Maya's timeline
    "key": ("text", _strokes(((8, 2), (14, 8), (8, 14), (2, 8), (8, 2)))),
    # a pose: a figure with its arms out
    "pose": ("text", _strokes(((6.5, 2), (9.5, 2), (9.5, 5), (6.5, 5), (6.5, 2)), ((8, 5), (8, 9.5)),
                              ((3, 7), (8, 6), (13, 7)), ((5, 14), (8, 9.5), (11, 14)))),
    # a module: a cube, three faces meeting at the centre
    "module": ("text", _strokes(((8, 2), (13.5, 5), (13.5, 11), (8, 14), (2.5, 11), (2.5, 5), (8, 2)),
                                ((2.5, 5), (8, 8), (13.5, 5)), ((8, 8), (8, 14)))),
}


def icon_folder(palette: Palette = DARK) -> pathlib.Path:
    """The folder of the theme's icon files, drawn on first use and named after the palette, so a changed colour
    never meets a stale file. A style sheet can only name an image by its path, which is why they are files."""
    key = hashlib.sha1(repr(palette).encode()).hexdigest()[:10]
    folder = pathlib.Path(tempfile.gettempdir()) / "bmaya_theme" / key
    if not all((folder / f"{name}.png").exists() for name in _ICONS):
        folder.mkdir(parents=True, exist_ok=True)
        for name, (field, painter_fn) in _ICONS.items():
            color = getattr(palette, field)
            _draw(folder / f"{name}.png", 16, 1, color, painter_fn)
            _draw(folder / f"{name}@2x.png", 16, 2, color, painter_fn)
    return folder


def icon(name: str, palette: Palette = DARK) -> QtGui.QIcon:
    """A theme icon for widgets that set one in code (button.setIcon(theme.icon("key"))). The names are the keys of
    _ICONS: chevron_down, chevron_right, chevron_up, check, dot (the last two are white, for the accent colour), and,
    in the text colour, plus, minus, mirror, rotate, scale, translate, key, pose and module."""
    return QtGui.QIcon(str(icon_folder(palette) / f"{name}.png"))


def stylesheet(palette: Palette = DARK) -> str:
    """The theme's Qt style sheet."""
    folder = icon_folder(palette)
    values = dataclasses.asdict(palette)
    values.update({f"icon_{name}": (folder / f"{name}.png").as_posix() for name in _ICONS})
    values["radius"] = RADIUS
    return _SHEET.substitute(values)


def apply(widget: QtWidgets.QWidget, palette: Palette = DARK) -> None:
    """Styles a top-level widget and everything inside it. A style sheet and the font are set on the widget itself,
    never on the application, so Maya's own windows keep their look."""
    font = widget.font()
    font.setPointSize(FONT_SIZE_PT)
    widget.setFont(font)
    # A plain QWidget paints no background of its own, and a rule for every QWidget would also paint the labels.
    window_palette = widget.palette()
    window_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette.window))
    widget.setPalette(window_palette)
    widget.setAutoFillBackground(True)
    widget.setStyleSheet(stylesheet(palette))
