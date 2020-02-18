# Copy Weights Tool
# bm_copyWeights.py

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.mel as mel

# Copy skin cluster from one target_meshect to another

def copy_weights(source_mesh=None, target_meshes=None, method="closestPoint"):
	"""Copies the skin cluster and weights from a target mesh to other meshes.

	:param source_mesh: The source mesh to copy from
	:param target_meshes: The destination meshes to copy to
	:param method: Derived from the copyWeights "surfaceAssociation" tag.\nOptions include "closestPoint", "rayCast", or "closestComponent"
	:type source_mesh: str
	:type target_meshes: list
	:type method: str
	:return: None
	"""

	sel = get_selection()

	if not sel:
		return

	use_verts = sel[0]
	source_mesh = sel[1]
	target_meshes = sel[2]

	# get the skin cluster
	try:
		skin_cluster = cmds.ls(cmds.listHistory(source_mesh), type="skinCluster")[0]
	except IndexError:
		# target_meshect has no skin cluster
		om.MGlobal.displayError("%s has no skinCluster to copy from." % source_mesh)
		return

	# if we're copying only to the selected verts, the destination mesh must already be skinned.
	if use_verts:
		# todo: check if they have the same influences
		cmds.copySkinWeights(sourceSkin=skin_cluster,
												 surfaceAssociation=method,
												 noMirror=1,
												 influenceAssociation=["oneToOne","closestJoint"],
												 normalize=1)
		om.MGlobal.displayInfo("Weights copied from %s to selected components." % source_mesh)

	else:
		# get info from skinCluster
		max_influences = cmds.skinCluster(skin_cluster, q=1, maximumInfluences=1)
		weight_distribution = cmds.skinCluster(skin_cluster, q=1, weightDistribution=1)
		maintain_max = cmds.skinCluster(skin_cluster, q=1, obeyMaxInfluences=1)
		# only returns joints that have non-zero influence
		joint_list = cmds.skinCluster(skin_cluster, q=1, weightedInfluence=1)

		# bind each target target_meshect using those settings
		for target_mesh in target_meshes:
			# select our bind joints
			cmds.select(joint_list, replace=1)	

			# look for and delete old clusters if they exist
			old_cstr = cmds.ls(cmds.listHistory(target_mesh), type="skinCluster")
			if len(old_cstr) > 0:
				cmds.delete(old_cstr)

			cmds.select(target_mesh, add=1)

			# add the skin cluster
			new_cstr = cmds.skinCluster(maximumInfluences=max_influences,
																	weightDistribution=weight_distribution,
																	obeyMaxInfluences=maintain_max,
																	toSelectedBones=True,
																	skinMethod=0,
																	bindMethod=0)

			# copy skin weights
			cmds.copySkinWeights(sourceSkin=skin_cluster,
													 destinationSkin=new_cstr[0],
													 surfaceAssociation=method,
													 noMirror=1,
													 influenceAssociation=["oneToOne","closestJoint"],
													 normalize=1)

			om.MGlobal.displayInfo("Weights copied from %s to %s"%(source_mesh, target_mesh))

			# prune joints with zero influences
			cmds.select(target_mesh, replace=1)
			mel.eval("removeUnusedInfluences;")


def get_selection():
	"""Returns our selection and determines if we'll copy only to vertices or not. 

	:return: [use_verts (bool), source_mesh (str), target_meshes (list)]
	:rtype: list
	"""

	use_verts = False

	sel = cmds.ls(sl=1)

	if len(sel) < 2: 
		om.MGlobal.displayError("Please select at least two meshes.")
		return None

	elif cmds.objectType(sel[0]) == "mesh" and len(sel) == 3:
		use_verts = True
		verts = cmds.polyListComponentConversion(sel[0], toVertex=1)
		source_mesh = sel[1]
		target_meshes = sel[2]
		return use_verts, source_mesh, target_meshes

	elif len(sel) > 1:
		use_verts = False
		source_mesh = sel[0]
		target_meshes = sel[1:]
		return use_verts, source_mesh, target_meshes

	else:
		return None

# copy the skin cluster weights from the first in selection to the rest
# copy_weights()





