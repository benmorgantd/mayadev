"""Reads a rig scene's shading into a textures.json and builds the shading from one (bmaya.core.asset.textures).

A look's model file holds meshes only. The textures sidecar says which image goes on which mesh and what it is for
(baseColor, normal, ...), keyed by meshId. save records it from the scene, and apply builds the shaders again from it,
every time a look is put on a rig, so a mesh never wears a shader the file doesn't describe. The shaders it builds are
tagged, and the next apply removes them first.

Only standardSurface is built and read. A slot reads one image file straight into its plug, through a bump2d for the
normal map. A network with anything else in it (a colour correct, a ramp) is reported and left out, not guessed at.
"""

from __future__ import annotations

import dataclasses
import os
import shutil

import maya.cmds as cmds

import bmaya.core.asset
import bmaya.core.asset.sourcecontrol
import bmaya.core.asset.textures
import bmaya.core.asset.versions
import bmaya.core.log

from bmaya.core.asset.textures import Material, MeshEntry, TextureMap, TexturesError

MATERIAL_TAG = "bmayaTextureMaterial"   # on every shading engine this module builds
BUILT_TYPES = ("standardSurface", "file", "place2dTexture", "bump2d")

# slot -> (the shader plug it feeds, the file node's output that goes in)
PLUGS = {
    "baseColor": ("baseColor", "outColor"),
    "emission": ("emissionColor", "outColor"),
    "opacity": ("opacity", "outColor"),
    "roughness": ("specularRoughness", "outAlpha"),
    "metalness": ("metalness", "outAlpha"),
    "normal": ("normalCamera", "outAlpha"),   # through a bump2d in tangent space mode
}
PLACE_2D_PLUGS = ("coverage", "translateFrame", "rotateFrame", "mirrorU", "mirrorV", "stagger", "wrapU", "wrapV",
                  "repeatUV", "offset", "rotateUV", "noiseUV", "vertexUvOne", "vertexUvTwo", "vertexUvThree",
                  "vertexCameraOne")


@dataclasses.dataclass
class ApplyReport:
    """What apply did: the meshes it textured, the meshes of the scene the file has no entry for, the entries with no
    mesh in the scene, and the image files the file names that aren't in the textures folder."""

    applied: list[str] = dataclasses.field(default_factory=list)
    unlisted: list[str] = dataclasses.field(default_factory=list)
    orphans: list[str] = dataclasses.field(default_factory=list)
    missing_files: list[str] = dataclasses.field(default_factory=list)


# ---- reading the scene -----------------------------------------------------------------------


def read_scene(meshes: dict[str, str], textures_folder: str, copy_in: bool = False) -> TextureMap:
    """The shading of the meshes (meshId -> mesh transform) as a TextureMap. A mesh with no material, or none that has
    a texture in it, gets no entry. Every image must be inside textures_folder: with copy_in the ones outside are
    copied in (an existing file of the same name is never overwritten), otherwise they are an error that names them.
    Raises TexturesError, and changes nothing, when nothing could be recorded or a file is outside the folder."""
    texture_map = TextureMap()
    outside: dict[str, str] = {}
    by_shader: dict[str, str] = {}
    for mesh_id, mesh in sorted(meshes.items(), key=lambda item: item[1]):
        shader = _shader_of(mesh)
        if shader is None:
            continue
        slots = {}
        for slot, (plug, _) in PLUGS.items():
            file_node = _file_node_on(shader, plug, slot, mesh)
            if file_node is not None:
                slots[slot] = _folder_relative(file_node, textures_folder, outside)
        if not slots:
            continue
        name = _short_name(shader)
        if name in by_shader and by_shader[name] != shader:
            raise TexturesError(f"Two different shaders are both called {name!r}: {by_shader[name]} and {shader}. "
                                f"Rename one, because a material is found by name.")
        by_shader[name] = shader
        material = Material(bmaya.core.asset.textures.DEFAULT_SHADER, slots)
        if texture_map.materials.setdefault(name, material) != material:
            raise TexturesError(f"The meshes that wear {shader} don't agree on its textures.")
        texture_map.meshes[mesh_id] = MeshEntry(_short_name(mesh), name)
    if not texture_map.meshes:
        raise TexturesError("No marked mesh has a standardSurface material with a texture file on it, so there is "
                            "nothing to record.")
    if outside:
        if not copy_in:
            raise TexturesError(f"These texture files are outside {textures_folder}: "
                                + ", ".join(sorted(outside)) + ". Copy them in, or save with copy_in=True.")
        os.makedirs(textures_folder, exist_ok=True)
        for source in sorted(outside):
            _copy_in(source, os.path.join(textures_folder, outside[source]))
    bmaya.core.asset.textures.check(texture_map)
    return texture_map


def _shader_of(mesh: str) -> str | None:
    """The standardSurface on a mesh, or None. A mesh on other shaders is reported, and one on the default shading
    group has none."""
    shapes = cmds.listRelatives(mesh, shapes=True, type="mesh", noIntermediate=True, fullPath=True) or []
    engines = [engine for engine in dict.fromkeys(cmds.listConnections(shapes, type="shadingEngine") or [])
               if engine != "initialShadingGroup"]
    if not engines:
        return None
    if len(engines) > 1:
        bmaya.core.log.warning(f"{mesh} has {len(engines)} materials: only {engines[0]} is recorded.")
    shaders = cmds.listConnections(engines[0] + ".surfaceShader", source=True, destination=False) or []
    if not shaders:
        return None
    if cmds.nodeType(shaders[0]) != "standardSurface":
        bmaya.core.log.warning(f"{mesh} wears {shaders[0]} ({cmds.nodeType(shaders[0])}): only standardSurface is "
                               f"recorded, so it gets no textures.")
        return None
    return shaders[0]


def _file_node_on(shader: str, plug: str, slot: str, mesh: str) -> str | None:
    """The file node that feeds a slot, straight in or through the normal map's bump2d. None when the slot has no
    texture, with a warning when it has a network that isn't one image."""
    source = (cmds.listConnections(f"{shader}.{plug}", source=True, destination=False) or [None])[0]
    if source is not None and cmds.nodeType(source) == "bump2d" and slot == "normal":
        source = (cmds.listConnections(f"{source}.bumpValue", source=True, destination=False) or [None])[0]
    if source is None:
        return None
    if cmds.nodeType(source) != "file":
        bmaya.core.log.warning(f"The {slot} of {shader} on {mesh} comes from {source} ({cmds.nodeType(source)}), "
                               f"not one image file, so it is not recorded.")
        return None
    return source


def _folder_relative(file_node: str, textures_folder: str, outside: dict[str, str]) -> str:
    """The file node's image as a path relative to the textures folder, written with '/'. An image outside the folder
    goes into outside (source -> the name it would be copied in as), and its bare file name is returned."""
    path = os.path.normpath(cmds.getAttr(file_node + ".fileTextureName"))
    folder = os.path.normpath(textures_folder)
    relative = os.path.relpath(path, folder) if os.path.splitdrive(path)[0].lower() == os.path.splitdrive(folder)[0].lower() \
        else os.pardir
    if relative.startswith(os.pardir):
        name = os.path.basename(path)
        outside[path] = name
        return name
    return relative.replace("\\", "/")


def _copy_in(source: str, target: str) -> None:
    if not os.path.isfile(source):
        raise TexturesError(f"Can't copy {source} in: it isn't a file.")
    if os.path.exists(target):
        if os.path.samefile(source, target):
            return
        raise TexturesError(f"Can't copy {source} in: {target} is another file with the same name.")
    shutil.copy2(source, target)


def save_file(asset: bmaya.core.asset.Asset, look: str, texture_map: TextureMap) -> str:
    """Writes the look's textures.json. An existing one is kept as a local version and checked out first, and a new
    one is added to source control (only that file, never the images beside it). Returns the path."""
    path = bmaya.core.asset.textures.get_path(asset.path("textures", look))
    existing = os.path.exists(path)
    if existing:
        bmaya.core.asset.versions.version(path, asset.root)
        bmaya.core.asset.sourcecontrol.current().checkout(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bmaya.core.asset.textures.write(path, texture_map)
    if not existing:
        bmaya.core.asset.sourcecontrol.current().add(path)
    return path


# ---- building the shading --------------------------------------------------------------------


def apply(texture_map: TextureMap, meshes: dict[str, str], textures_folder: str, namespace: str = "") -> ApplyReport:
    """Builds the shading of the meshes (meshId -> mesh transform) from the map, in the namespace. The shaders this
    module built in the namespace before are removed first, so the result is only what the file says. A mesh with no
    entry keeps what it has, and is listed in the report. Nothing here fails for a missing image: the file node is
    still made, so the path is there to fix, and the report lists it."""
    report = ApplyReport()
    report.unlisted = sorted(_short_name(mesh) for mesh_id, mesh in meshes.items() if mesh_id not in texture_map.meshes)
    report.orphans = sorted(entry.name for mesh_id, entry in texture_map.meshes.items() if mesh_id not in meshes)
    report.missing_files = bmaya.core.asset.textures.missing_files(texture_map, textures_folder)
    remove_materials(namespace)
    wanted = [mesh_id for mesh_id in texture_map.meshes if mesh_id in meshes]
    release_meshes([meshes[mesh_id] for mesh_id in wanted])
    current = cmds.namespaceInfo(currentNamespace=True, absoluteName=True)
    if namespace:
        cmds.namespace(setNamespace=":" + namespace.strip(":"))
    try:
        engines = {name: _build_material(name, texture_map.materials[name], textures_folder)
                   for name in texture_map.materials_of(wanted)}
    finally:
        cmds.namespace(setNamespace=current)
    for mesh_id in wanted:
        cmds.sets(meshes[mesh_id], edit=True, forceElement=engines[texture_map.meshes[mesh_id].material])
        report.applied.append(meshes[mesh_id])
    return report


def remove_materials(namespace: str = "") -> list[str]:
    """Deletes the materials apply built in the namespace: each tagged shading engine with its shader and the file,
    place2dTexture and bump2d nodes feeding it. A mesh on one falls back to the default shading group. Returns the
    shading engines removed."""
    pattern = f"{namespace.strip(':')}:*" if namespace else "*"
    engines = [engine for engine in cmds.ls(pattern, type="shadingEngine") or [] if cmds.attributeQuery(MATERIAL_TAG, node=engine, exists=True)]
    for engine in engines:
        built = [node for node in cmds.listHistory(engine) or [] if cmds.nodeType(node) in BUILT_TYPES]
        cmds.delete(engine)
        built = [node for node in built if cmds.objExists(node)]
        if built:
            cmds.delete(built)
    return engines


def release_meshes(meshes: list[str]) -> list[str]:
    """Puts each mesh on the default shading group, and deletes the shading engines that leaves empty with their shader
    and file nodes, so what the textures file builds replaces a material someone made by hand instead of sitting
    beside it. An engine another mesh still wears is kept. Returns the engines deleted."""
    engines = []
    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh", noIntermediate=True, fullPath=True) or []
        for engine in dict.fromkeys(cmds.listConnections(shapes, type="shadingEngine") or []):
            if engine != "initialShadingGroup":
                cmds.sets(mesh, edit=True, forceElement="initialShadingGroup")
                engines.append(engine)
    deleted = []
    for engine in dict.fromkeys(engines):
        if cmds.sets(engine, query=True):
            continue
        built = [node for node in cmds.listHistory(engine) or [] if cmds.nodeType(node) in BUILT_TYPES]
        cmds.delete(engine)
        built = [node for node in built if cmds.objExists(node)]
        if built:
            cmds.delete(built)
        deleted.append(engine)
    return deleted


def _build_material(name: str, material: Material, textures_folder: str) -> str:
    """One standardSurface and its shading engine, with a file node per slot. Returns the shading engine."""
    shader = cmds.shadingNode(material.shader, asShader=True, name=name)
    engine = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.addAttr(engine, longName=MATERIAL_TAG, attributeType="bool")
    cmds.connectAttr(shader + ".outColor", engine + ".surfaceShader")
    spaces = bmaya.core.asset.textures.SHADERS[material.shader]
    for slot, file in material.slots.items():
        plug, output = PLUGS[slot]
        file_node = _build_file(f"{name}_{slot}", os.path.join(textures_folder, *file.split("/")), spaces[slot],
                                single_channel=output == "outAlpha")
        if slot == "normal":
            bump = cmds.shadingNode("bump2d", asUtility=True, name=f"{name}_normalBump")
            cmds.setAttr(bump + ".bumpInterp", 1)   # tangent space normals
            cmds.connectAttr(f"{file_node}.{output}", bump + ".bumpValue")
            cmds.connectAttr(bump + ".outNormal", f"{shader}.{plug}")
        else:
            cmds.connectAttr(f"{file_node}.{output}", f"{shader}.{plug}")
    if "emission" in material.slots:
        cmds.setAttr(shader + ".emission", 1)   # the emission colour does nothing at weight 0
    return engine


def _build_file(name: str, path: str, color_space: str, single_channel: bool) -> str:
    file_node = cmds.shadingNode("file", asTexture=True, name=name)
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=name + "_place")
    for plug in PLACE_2D_PLUGS:
        cmds.connectAttr(f"{place}.{plug}", f"{file_node}.{plug}")
    cmds.connectAttr(place + ".outUV", file_node + ".uvCoord")
    cmds.connectAttr(place + ".outUvFilterSize", file_node + ".uvFilterSize")
    cmds.setAttr(file_node + ".fileTextureName", path.replace("\\", "/"), type="string")
    cmds.setAttr(file_node + ".colorSpace", color_space, type="string")
    if single_channel:
        cmds.setAttr(file_node + ".alphaIsLuminance", True)
    return file_node


def _short_name(node: str) -> str:
    return node.split("|")[-1].split(":")[-1]
