"""The Qt Prompter: every question a tool asks, as a Qt dialog. No Maya: the parent window comes from the caller
(RigModules design/mayadev-ui.md, D49)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6 import QtWidgets

from bmaya.maya_ui.widgets import DataclassForm


def _no_parent() -> QtWidgets.QWidget | None:
    return None


class QtPrompter:
    """Implements bmaya.core.prompts.Prompter with Qt dialogs. parent_window gives the window each dialog sits on,
    read per question so a window opened after registration is used."""

    def __init__(self, parent_window: Callable[[], QtWidgets.QWidget | None] = _no_parent) -> None:
        self._parent_window = parent_window

    def ask_text(self, title: str, message: str, default: str = "") -> str | None:
        text, ok = QtWidgets.QInputDialog.getText(self._parent_window(), title, message, text=default)
        return (text.strip() or None) if ok else None

    def choose(self, title: str, message: str, options: Sequence[str]) -> str | None:
        item, ok = QtWidgets.QInputDialog.getItem(self._parent_window(), title, message, list(options), 0, False)
        return item if ok else None

    def confirm(self, title: str, message: str, accept: str = "OK") -> bool:
        box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Question, title, message, parent=self._parent_window())
        accept_button = box.addButton(accept, QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        cancel_button = box.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_button)
        box.exec()
        return box.clickedButton() is accept_button

    def ask_file(self, title: str, file_filter: str, save: bool, folder: str = "") -> str | None:
        dialog = QtWidgets.QFileDialog.getSaveFileName if save else QtWidgets.QFileDialog.getOpenFileName
        path, _ = dialog(self._parent_window(), title, folder, file_filter)
        return path or None

    def ask_folder(self, title: str, folder: str = "") -> str | None:
        return QtWidgets.QFileDialog.getExistingDirectory(self._parent_window(), title, folder) or None

    def ask_form(self, title: str, value):
        dialog = FormDialog(title, value, self._parent_window())
        return dialog.result_value if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted else None


class FormDialog(QtWidgets.QDialog):
    """A DataclassForm with OK and Cancel. OK stays open, with the problem shown, while a field's value is
    invalid."""

    def __init__(self, title: str, value: object, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.result_value = None
        layout = QtWidgets.QVBoxLayout(self)
        self.form = DataclassForm(value, self)
        layout.addWidget(self.form)
        self.problem = QtWidgets.QLabel("")
        self.problem.setStyleSheet("color: #e05555;")
        layout.addWidget(self.problem)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        try:
            self.result_value = self.form.value()
        except ValueError as err:
            self.problem.setText(str(err))
            return
        super().accept()
