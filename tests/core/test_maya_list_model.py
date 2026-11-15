"""ListModel offscreen in mayapy (RigModules D51, design/library-browser.md). It needs no plugin and no rig: it is a
Qt model over a Python list.

Run with tests/core/run.bat (the Maya half), or: mayapy -m unittest discover -s tests/core -p "test_maya_*.py"
"""

import dataclasses
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None


def setUpModule():
    if maya is None:
        raise unittest.SkipTest("needs mayapy")
    from PySide6 import QtWidgets
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@dataclasses.dataclass(frozen=True)
class Item:
    name: str
    source: str


ITEMS = [Item("fist", "user"), Item("idle", "approved"), Item("wave", "user")]


class ListModelTests(unittest.TestCase):

    def setUp(self):
        from PySide6 import QtCore
        from bmaya.maya_ui.widgets import ListModel

        self.qt = QtCore.Qt
        self.ListModel = ListModel
        self.roles = {self.qt.ItemDataRole.DisplayRole: lambda item: item.name,
                      self.qt.ItemDataRole.ToolTipRole: lambda item: f"{item.name} ({item.source})",
                      self.qt.ItemDataRole.UserRole: lambda item: item}

    def index(self, model, row, column=0):
        return model.index(row, column)

    def test_rows_and_roles_come_from_the_items(self):
        model = self.ListModel(self.roles, ITEMS)
        self.assertEqual((model.rowCount(), model.columnCount()), (3, 1))
        self.assertEqual(model.data(self.index(model, 1)), "idle")
        self.assertEqual(model.data(self.index(model, 1), self.qt.ItemDataRole.ToolTipRole), "idle (approved)")
        self.assertIs(model.data(self.index(model, 2), self.qt.ItemDataRole.UserRole), ITEMS[2])
        self.assertIsNone(model.data(self.index(model, 0), self.qt.ItemDataRole.DecorationRole), "a role with no function is empty")
        self.assertIsNone(model.data(model.index(9, 0)), "an index that is not a row is empty")
        self.assertIs(model.item(0), ITEMS[0])

    def test_set_items_resets_the_model_and_tells_its_views(self):
        model = self.ListModel(self.roles, ITEMS)
        events = []
        model.modelAboutToBeReset.connect(lambda: events.append("about"))
        model.modelReset.connect(lambda: events.append("reset"))
        model.set_items(ITEMS[:1])
        self.assertEqual((events, model.rowCount(), model.items), (["about", "reset"], 1, ITEMS[:1]))
        model.set_items([])
        self.assertEqual(model.rowCount(), 0)

    def test_the_model_does_not_alias_the_list_it_was_given(self):
        items = list(ITEMS)
        model = self.ListModel(self.roles, items)
        items.clear()
        self.assertEqual(model.rowCount(), 3)
        model.items.clear()
        self.assertEqual(model.rowCount(), 3)

    def test_row_of_finds_the_selection_again_after_a_reset(self):
        model = self.ListModel(self.roles, ITEMS)
        selected = ITEMS[2]
        model.set_items([Item("wave", "user"), Item("a", "user")])   # new objects, same names
        self.assertEqual(model.row_of(lambda item: item.name == selected.name), 0)
        self.assertEqual(model.row_of(lambda item: item.name == "gone"), -1)

    def test_columns_give_a_table_its_headers_and_cells_and_roles_apply_to_every_column(self):
        from PySide6 import QtWidgets
        columns = [("Name", lambda item: item.name), ("Source", lambda item: item.source.title())]
        model = self.ListModel(self.roles, ITEMS, columns)
        self.assertEqual(model.columnCount(), 2)
        self.assertEqual([model.data(self.index(model, 0, c)) for c in (0, 1)], ["fist", "User"])
        self.assertEqual(model.headerData(1, self.qt.Orientation.Horizontal), "Source")
        self.assertIsNone(model.headerData(5, self.qt.Orientation.Horizontal))
        self.assertIsNone(model.headerData(0, self.qt.Orientation.Vertical))
        self.assertEqual(model.data(self.index(model, 1, 1), self.qt.ItemDataRole.ToolTipRole), "idle (approved)")

        table = QtWidgets.QTableView()
        table.setModel(model)
        table.selectRow(1)
        self.assertEqual(table.selectionModel().selectedRows()[0].row(), 1)

    def test_a_list_view_and_a_filter_proxy_work_over_it(self):
        from PySide6 import QtCore, QtWidgets
        model = self.ListModel(self.roles, ITEMS)
        view = QtWidgets.QListView()
        view.setModel(model)
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(self.qt.CaseSensitivity.CaseInsensitive)
        proxy.setFilterFixedString("I")
        self.assertEqual([proxy.data(proxy.index(row, 0)) for row in range(proxy.rowCount())], ["fist", "idle"])

    def test_a_model_has_no_children_below_a_row(self):
        model = self.ListModel(self.roles, ITEMS)
        self.assertEqual((model.rowCount(model.index(0, 0)), model.columnCount(model.index(0, 0))), (0, 0))


if __name__ == "__main__":
    unittest.main()
