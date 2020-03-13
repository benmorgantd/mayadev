from pymel.core import *
import time

__all__ = ["blendBoundary"]

def gatherBorderInfo(meshObj):
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
    
def blendBoundary(meshA, meshB, distanceTolerance=0.001):
    startTime = time.time()

    meshA = PyNode(meshA)
    meshB = PyNode(meshB)

    vertsA = meshA.verts
    vertsB = meshB.verts

    borderA = [vert for vert in vertsA if vert.isOnBoundary()]
    borderB = [vert for vert in vertsB if vert.isOnBoundary()]

    pointsB = [vert.getPosition(space='world') for vert in borderB]

    for vertA in borderA:
        indexA = vertA.index()
        pointA = vertA.getPosition(space='world')
        normalA = vertA.getNormal(space='world')

        for j in range(len(borderB)):
            if (pointA - pointsB[j]).length() <= distanceTolerance:
                indexB = borderB[j].index()

                averageNormal = (normalA + borderB[j].getNormal(space='world')) / 2.0

                meshA.setVertexNormal(averageNormal, indexA)
                meshB.setVertexNormal(averageNormal, indexB)
                
                borderB.pop(j)
                pointsB.pop(j)

                break

    meshA.updateSurface()
    meshB.updateSurface()

    displayInfo('Blending complete for {0} and {1} in {2} seconds.'.format(meshA, meshB, time.time() - startTime))



    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    