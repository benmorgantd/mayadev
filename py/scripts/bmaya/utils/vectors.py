import maya.OpenMaya as om


class Vector(object):
    """A simple wrapper for MVector."""

    def __init__(self, vector):
        self.vector = om.MVector(*vector)

    @property
    def asPoint(self):
        return om.MPoint(self.vector.x, self.vector.y, self.vector.z)

    @property
    def asList(self):
        return [self.vector.x, self.vector.y, self.vector.z]


