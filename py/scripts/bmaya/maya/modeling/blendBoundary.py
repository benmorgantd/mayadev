"""Purpose:
This is a utility for blending the vertex normals between two separate meshes where vertices have the same world space position.
"""

import pymel.core as pm
import time
from bmaya.core import log

__all__ = ["blend_boundary"]


def gather_border_info(meshObj):
    # the majority of our time is spent in here
    border = []
    points = []
    normals = []

    for vert in meshObj.verts:
        if vert.isOnBoundary():
            border.append(vert)
            points.append(vert.getPosition(space='world'))
            normals.append(vert.getNormal(space='world'))

    return border, points, normals


def blend_boundary(mesh_a, mesh_b, distance_tolerance=0.001):
    startTime = time.time()

    mesh_a = pm.PyNode(mesh_a)
    mesh_b = pm.PyNode(mesh_b)

    verts_a = mesh_a.verts
    verts_b = mesh_b.verts

    border_a = [vert for vert in verts_a if vert.isOnBoundary()]
    border_b = [vert for vert in verts_b if vert.isOnBoundary()]

    points_b = [vert.getPosition(space='world') for vert in border_b]

    for vert_a in border_a:
        indexA = vert_a.index()
        pointA = vert_a.getPosition(space='world')
        normalA = vert_a.getNormal(space='world')

        for j in range(len(border_b)):
            if (pointA - points_b[j]).length() <= distance_tolerance:
                indexB = border_b[j].index()

                averageNormal = (
                    normalA + border_b[j].getNormal(space='world')) / 2.0

                mesh_a.setVertexNormal(averageNormal, indexA)
                mesh_b.setVertexNormal(averageNormal, indexB)

                border_b.pop(j)
                points_b.pop(j)

                break

    mesh_a.updateSurface()
    mesh_b.updateSurface()

    log.info(
        'Blending complete for {0} and {1} in {2} seconds.'.format(
            mesh_a,
            mesh_b,
            time.time() -
            startTime))
