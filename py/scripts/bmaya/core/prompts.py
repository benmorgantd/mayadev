"""Questions a tool asks the user, as a protocol, so the code that asks never imports a UI.

A workflow takes prompter=None and asks current(), the prompter registered for the session. A GUI session registers
Qt dialogs (bmaya.maya_ui.startup). With nothing registered, NoPrompter raises on the first question, so a mayapy
run fails with the question instead of waiting on a dialog. Tests pass a ScriptedPrompter with the answers
(RigModules design/mayadev-ui.md, D49).

Every method returns None (False for confirm) when the user cancels.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Sequence
from typing import Protocol, TypeVar

T = TypeVar("T")


class ImagePath(str):
    """A form field holding the path of an image file. A form shows it as a line with a Browse button; "" is no
    image."""


class PromptError(RuntimeError):
    """A question that nothing could answer."""


@dataclasses.dataclass(frozen=True)
class Question:
    """One question as asked: the method's name, its title and message, and its options or default."""

    kind: str
    title: str
    message: str = ""
    options: tuple = ()
    default: object = None


class Prompter(Protocol):
    def ask_text(self, title: str, message: str, default: str = "") -> str | None:
        """A line of text. None when cancelled or left empty."""

    def choose(self, title: str, message: str, options: Sequence[str]) -> str | None:
        """One of options."""

    def confirm(self, title: str, message: str, accept: str = "OK") -> bool:
        """True when the user accepts. accept is the label of the button that does."""

    def ask_file(self, title: str, file_filter: str, save: bool, folder: str = "") -> str | None:
        """A file to save to (save) or open. file_filter is Qt's: "Pose files (*.json)", ";;" between filters."""

    def ask_folder(self, title: str, folder: str = "") -> str | None:
        """An existing folder."""

    def ask_form(self, title: str, value: T) -> T | None:
        """value, a dataclass instance, with its fields edited. A field's type hint picks its editor."""


class NoPrompter:
    """The default: raises on every question, naming it."""

    def _raise(self, title: str, message: str = "") -> None:
        text = f"{title}: {message}" if message else title
        raise PromptError(f"'{text}' needs an answer, and this session has no prompter. Pass the answer to the plain "
                          "function the tool calls, or pass a prompter.")

    def ask_text(self, title, message, default=""):
        self._raise(title, message)

    def choose(self, title, message, options):
        self._raise(title, message)

    def confirm(self, title, message, accept="OK"):
        self._raise(title, message)

    def ask_file(self, title, file_filter, save, folder=""):
        self._raise(title)

    def ask_folder(self, title, folder=""):
        self._raise(title)

    def ask_form(self, title, value):
        self._raise(title)


class ScriptedPrompter:
    """Answers questions in order from a list, and records each question in asked. A question past the last answer
    raises PromptError naming it. For tests and batch jobs that drive an interactive workflow."""

    def __init__(self, answers: Iterable[object] = ()) -> None:
        self._answers = list(answers)
        self.asked: list[Question] = []

    def _answer(self, question: Question) -> object:
        self.asked.append(question)
        if not self._answers:
            raise PromptError(f"No scripted answer for {question.kind} '{question.title}: {question.message}'.")
        return self._answers.pop(0)

    def ask_text(self, title, message, default=""):
        return self._answer(Question("ask_text", title, message, default=default))

    def choose(self, title, message, options):
        return self._answer(Question("choose", title, message, tuple(options)))

    def confirm(self, title, message, accept="OK"):
        return bool(self._answer(Question("confirm", title, message, (accept,))))

    def ask_file(self, title, file_filter, save, folder=""):
        return self._answer(Question("ask_file", title, file_filter, default=folder))

    def ask_folder(self, title, folder=""):
        return self._answer(Question("ask_folder", title, default=folder))

    def ask_form(self, title, value):
        return self._answer(Question("ask_form", title, default=value))

    @property
    def remaining(self) -> int:
        """Answers not used yet."""
        return len(self._answers)


_prompter: Prompter = NoPrompter()


def current() -> Prompter:
    """The prompter registered for this session, else NoPrompter."""
    return _prompter


def register_prompter(prompter: Prompter) -> None:
    """Fills the prompter slot. Called only from a layer's startup.register()."""
    global _prompter
    _prompter = prompter


def reset_prompter() -> None:
    """Puts the default back: NoPrompter."""
    global _prompter
    _prompter = NoPrompter()
