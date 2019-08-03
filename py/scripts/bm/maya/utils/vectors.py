import maya.OpenMaya as om


class Vector(object):
    """A simple wrapper for MVector."""

    def __init__(self, vector):
        self.vector = om.MVector(*vector)

    def toPoint(self):
        return om.MPoint(self.vector.x, self.vector.y, self.vector.z)

    def toList(self):
        return [self.vector.x, self.vector.y, self.vector.z]


