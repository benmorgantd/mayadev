"""bmaya.core.fieldset in plain Python: the fields edited across a selection and what their values are over it
(RigModules D61).

Run with tests/core/run.bat, or: python -m unittest discover -s tests/core -p "test_core_*.py"
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.fieldset import FieldSpec, FieldState, combine, same  # noqa: E402


class Combine(unittest.TestCase):

    def test_no_values_is_an_empty_state(self):
        self.assertEqual(combine([]), FieldState(None, False, 0))

    def test_one_value_is_that_value(self):
        self.assertEqual(combine(["Left"]), FieldState("Left", False, 1))

    def test_equal_values_are_one_value(self):
        self.assertEqual(combine([True, True, True]), FieldState(True, False, 3))

    def test_different_values_are_mixed_with_no_value(self):
        self.assertEqual(combine(["Left", "Right", "Left"]), FieldState(None, True, 3))

    def test_a_false_value_is_not_mistaken_for_no_value(self):
        state = combine([False, False])
        self.assertEqual((state.value, state.mixed), (False, False))

    def test_floats_within_the_tolerance_are_one_value(self):
        self.assertFalse(combine([1.0, 1.0 + 1e-9]).mixed)

    def test_floats_further_apart_are_mixed(self):
        self.assertTrue(combine([1.0, 1.001]).mixed)

    def test_a_float_and_an_int_that_are_equal_are_one_value(self):
        self.assertFalse(combine([1, 1.0]).mixed)


class Same(unittest.TestCase):

    def test_a_float_against_text_is_not_the_same(self):
        self.assertFalse(same(1.0, "x"))

    def test_text_is_compared_exactly(self):
        self.assertTrue(same("a", "a"))
        self.assertFalse(same("a", "A"))


class Spec(unittest.TestCase):

    def test_a_known_kind_is_accepted(self):
        for kind in ("choice", "text", "bool", "float"):
            self.assertEqual(FieldSpec("x", "X", kind).kind, kind)

    def test_an_unknown_kind_is_refused_naming_the_field(self):
        with self.assertRaisesRegex(ValueError, "'x'.*'colour'"):
            FieldSpec("x", "X", "colour")


if __name__ == "__main__":
    unittest.main()
