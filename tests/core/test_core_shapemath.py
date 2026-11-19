"""bmaya.core.shapemath in plain Python: a control's shapeTransform as translate, rotate and scale (RigModules D26,
D61). The matrices are worked out by hand from Maya's row-vector convention: a rotation of 90 degrees about X sends the
Y axis onto Z, and about Z sends the X axis onto Y.

Run with tests/core/run.bat, or: python -m unittest discover -s tests/core -p "test_core_*.py"
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.shapemath import IDENTITY, compose, decompose  # noqa: E402


class Close(unittest.TestCase):

    def assertAll(self, actual, expected, places=9):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=places, msg=f"{actual} != {expected}")


class Compose(Close):

    def test_nothing_is_the_identity(self):
        self.assertAll(compose((0, 0, 0), (0, 0, 0), (1, 1, 1)), IDENTITY)

    def test_scale_is_the_diagonal_and_translate_the_last_row(self):
        self.assertAll(compose((1, 2, 3), (0, 0, 0), (2, 3, 4)),
                       (2, 0, 0, 0, 0, 3, 0, 0, 0, 0, 4, 0, 1, 2, 3, 1))

    def test_x_90_sends_y_onto_z(self):
        self.assertAll(compose((0, 0, 0), (90, 0, 0), (1, 1, 1)), (1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1))

    def test_y_90_sends_z_onto_x(self):
        self.assertAll(compose((0, 0, 0), (0, 90, 0), (1, 1, 1)), (0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1))

    def test_z_90_sends_x_onto_y(self):
        self.assertAll(compose((0, 0, 0), (0, 0, 90), (1, 1, 1)), (0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))

    def test_scale_multiplies_each_axis_row_after_rotating(self):
        self.assertAll(compose((0, 0, 0), (0, 0, 90), (2, 3, 4)), (0, 2, 0, 0, -3, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 1))


class Decompose(Close):

    def test_identity(self):
        self.assertEqual(decompose(IDENTITY), ((0, 0, 0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))

    def test_the_hand_written_matrices_split_back(self):
        translate, rotate, scale = decompose((0, 2, 0, 0, -3, 0, 0, 0, 0, 0, 4, 0, 5, 6, 7, 1))
        self.assertAll(translate, (5, 6, 7))
        self.assertAll(rotate, (0, 0, 90))
        self.assertAll(scale, (2, 3, 4))

    def test_a_mirror_has_a_negative_x_scale_and_no_rotation(self):
        translate, rotate, scale = decompose((-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 3, 0, 0, 1))
        self.assertAll(scale, (-1, 1, 1))
        self.assertAll(rotate, (0, 0, 0))
        self.assertAll(translate, (3, 0, 0))

    def test_a_matrix_that_is_not_16_numbers_is_refused(self):
        with self.assertRaisesRegex(ValueError, "16 numbers, not 4"):
            decompose((1, 0, 0, 1))

    def test_an_axis_of_no_length_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no length"):
            decompose((0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))


class RoundTrip(Close):
    CASES = (
        ((0, 0, 0), (0, 0, 0), (1, 1, 1)),
        ((1, -2, 3), (30, 45, 60), (1, 2, 3)),
        ((0, 0, 0), (-70, 10, 170), (0.5, 0.5, 0.5)),
        ((4, 5, 6), (10, -80, -20), (3, 1, 2)),
        ((0, 0, 0), (0, 0, 0), (-1, 1, 1)),
        ((1, 1, 1), (15, 25, 35), (-2, 3, 1.5)),
    )

    def test_composing_what_was_decomposed_gives_the_same_matrix(self):
        for translate, rotate, scale in self.CASES:
            matrix = compose(translate, rotate, scale)
            self.assertAll(compose(*decompose(matrix)), matrix)

    def test_the_parts_come_back_for_a_proper_rotation(self):
        translate, rotate, scale = decompose(compose((1, -2, 3), (30, 45, 60), (1, 2, 3)))
        self.assertAll(translate, (1, -2, 3))
        self.assertAll(rotate, (30, 45, 60))
        self.assertAll(scale, (1, 2, 3))

    def test_a_rotation_looking_straight_along_an_axis_still_gives_the_same_matrix(self):
        for rotate in ((30, 90, 0), (10, 90, 20), (-40, -90, 15)):
            matrix = compose((0, 1, 0), rotate, (2, 2, 2))
            self.assertAll(compose(*decompose(matrix)), matrix)

    def test_a_scale_that_is_negative_in_y_comes_back_as_the_same_shape(self):
        # The sign moves to the X scale: the matrix is the same, which is all a shape needs.
        matrix = compose((0, 0, 0), (0, 0, 0), (1, -1, 1))
        self.assertAll(compose(*decompose(matrix)), matrix)
        self.assertTrue(math.isclose(abs(decompose(matrix)[2][0]), 1.0))


if __name__ == "__main__":
    unittest.main()
