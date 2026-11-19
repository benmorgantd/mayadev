"""A control's shapeTransform as translate, rotate and scale, and back (RigModules D26, D61). No Maya, no Qt.

shapeTransform is a 4x4 matrix in Maya's row-vector convention, written as 16 numbers row by row: the first three
rows are the shape's X, Y and Z axes (each scaled), and the last row is the translation. Rotation is in degrees, in
XYZ order, which is what Maya's rotate channels use by default. A matrix with a reflection (the mirror of a shape has
one) has a negative X scale, so decompose and compose round trip it. A matrix with a shear does not round trip: the
shear is lost. The shapes the editor writes never have one.

    matrix = compose((0, 1, 0), (0, 0, 90), (2, 2, 2))
    translate, rotate, scale = decompose(matrix)
"""

from __future__ import annotations

import math
from collections.abc import Sequence

IDENTITY = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
_EPSILON = 1e-9


def decompose(matrix: Sequence[float]) -> tuple[tuple[float, float, float], tuple[float, float, float],
                                                 tuple[float, float, float]]:
    """(translate, rotate in degrees, scale) of a 16 number shapeTransform. Raises ValueError for a matrix that is not
    16 numbers or has an axis of no length."""
    if len(matrix) != 16:
        raise ValueError(f"A shapeTransform is 16 numbers, not {len(matrix)}.")
    rows = [list(matrix[0:3]), list(matrix[4:7]), list(matrix[8:11])]
    scale = [math.sqrt(sum(value * value for value in row)) for row in rows]
    if min(scale) < _EPSILON:
        raise ValueError("A shapeTransform with an axis of no length can't be split into scale and rotation.")
    if _determinant(rows) < 0.0:
        scale[0] = -scale[0]
    unit = [[value / scale[i] for value in row] for i, row in enumerate(rows)]
    sin_y = max(-1.0, min(1.0, -unit[0][2]))
    ry = math.asin(sin_y)
    if abs(sin_y) < 1.0 - _EPSILON:
        rx = math.atan2(unit[1][2], unit[2][2])
        rz = math.atan2(unit[0][1], unit[0][0])
    else:   # looking straight along an axis: x and z turn the same way, so z is taken as 0
        rz = 0.0
        rx = math.atan2(unit[1][0] * sin_y, unit[1][1])
    rotate = (math.degrees(rx), math.degrees(ry), math.degrees(rz))
    return (matrix[12], matrix[13], matrix[14]), rotate, (scale[0], scale[1], scale[2])


def compose(translate: Sequence[float], rotate: Sequence[float], scale: Sequence[float]) -> tuple[float, ...]:
    """The 16 number shapeTransform of a translate, a rotate in degrees (XYZ) and a scale."""
    sx, sy, sz = (math.sin(math.radians(angle)) for angle in rotate)
    cx, cy, cz = (math.cos(math.radians(angle)) for angle in rotate)
    rows = (
        (cy * cz, cy * sz, -sy),
        (sx * sy * cz - cx * sz, sx * sy * sz + cx * cz, sx * cy),
        (cx * sy * cz + sx * sz, cx * sy * sz - sx * cz, cx * cy),
    )
    out: list[float] = []
    for row, size in zip(rows, scale):
        out.extend((row[0] * size, row[1] * size, row[2] * size, 0.0))
    out.extend((float(translate[0]), float(translate[1]), float(translate[2]), 1.0))
    return tuple(out)


def _determinant(rows: list[list[float]]) -> float:
    a, b, c = rows
    return (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))
