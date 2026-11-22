"""textures.json: which texture goes on which mesh, and what each one is for.

The sidecar of a look's textures folder, as the weight files are the sidecar of its skeleton: a model file holds
meshes only, and Load Textures builds the shaders from this file every time a look is put on a rig, so the shading is
always valid whatever the scene held before.

    looks/default/textures/textures.json
    {
      "formatVersion": 1,
      "materials": {
        "gun_mat": {"shader": "standardSurface",
                    "slots": {"baseColor": "gun_albedo.png", "normal": "gun_normal.png", "roughness": "gun_rough.png"}}
      },
      "meshes": {"3f2a...": {"meshName": "gun_geo", "material": "gun_mat"}}
    }

A mesh is found by its meshId, as skin weights are, so a renamed mesh keeps its textures: meshName is only there for
a person reading the file. Meshes name a material and several can share one. A slot's file is a path relative to the
textures folder, so a moved look still finds its files. Plain Python, no Maya.
"""

from __future__ import annotations

import dataclasses
import os
import posixpath

from .project import ProjectError, read_json, write_json

FILE_NAME = "textures.json"
FORMAT_VERSION = 1

# The shaders Load Textures can build, and each one's slots with the colour space of the image that feeds it. Colour
# images are read as sRGB, and data images (a normal map, roughness) as raw values.
SHADERS = {
    "standardSurface": {
        "baseColor": "sRGB",
        "emission": "sRGB",
        "normal": "Raw",
        "roughness": "Raw",
        "metalness": "Raw",
        "opacity": "Raw",
    },
}
DEFAULT_SHADER = "standardSurface"


class TexturesError(RuntimeError):
    """A textures.json that can't be read or doesn't make sense, or a scene whose shading can't be recorded."""


@dataclasses.dataclass(frozen=True)
class Material:
    """One shader: its type and the image file of each slot it uses."""

    shader: str = DEFAULT_SHADER
    slots: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class MeshEntry:
    """A mesh of the look, by name, and the material it wears."""

    name: str
    material: str


@dataclasses.dataclass
class TextureMap:
    """The whole file: materials by name and meshes by meshId."""

    materials: dict[str, Material] = dataclasses.field(default_factory=dict)
    meshes: dict[str, MeshEntry] = dataclasses.field(default_factory=dict)

    def materials_of(self, mesh_ids) -> list[str]:
        """The names of the materials the given meshIds wear, in file order, each once."""
        used = {self.meshes[mesh_id].material for mesh_id in mesh_ids if mesh_id in self.meshes}
        return [name for name in self.materials if name in used]

    def files(self) -> list[str]:
        """Every image file the map names, sorted, each once."""
        return sorted({file for material in self.materials.values() for file in material.slots.values()})


def get_path(textures_folder: str) -> str:
    """Where the sidecar of a textures folder is."""
    return os.path.join(textures_folder, FILE_NAME)


def missing_files(texture_map: TextureMap, textures_folder: str) -> list[str]:
    """The image files the map names that aren't in the textures folder."""
    return [file for file in texture_map.files() if not os.path.isfile(os.path.join(textures_folder, *file.split("/")))]


def check(texture_map: TextureMap) -> None:
    """Raises TexturesError for anything Load Textures couldn't build: an unknown shader or slot, a file that isn't
    a plain relative path, a mesh naming a material the file doesn't have."""
    for name, material in texture_map.materials.items():
        if not name or not isinstance(name, str):
            raise TexturesError(f"A material needs a name: {name!r}.")
        if material.shader not in SHADERS:
            raise TexturesError(f"The material {name!r} has the shader {material.shader!r}. "
                                f"Known shaders: {', '.join(SHADERS)}.")
        for slot, file in material.slots.items():
            if slot not in SHADERS[material.shader]:
                raise TexturesError(f"The material {name!r} has the slot {slot!r}, which {material.shader} doesn't "
                                    f"have. Its slots: {', '.join(SHADERS[material.shader])}.")
            _check_file(name, slot, file)
    for mesh_id, entry in texture_map.meshes.items():
        if entry.material not in texture_map.materials:
            raise TexturesError(f"The mesh {entry.name!r} ({mesh_id}) wears the material {entry.material!r}, which the "
                                f"file doesn't have.")


def _check_file(material: str, slot: str, file: object) -> None:
    where = f"The {slot} of the material {material!r}"
    if not isinstance(file, str) or not file:
        raise TexturesError(f"{where} needs a file name, not {file!r}.")
    if "\\" in file or posixpath.isabs(file) or ":" in file or ".." in file.split("/"):
        raise TexturesError(f"{where} is {file!r}: use a path inside the textures folder, written with '/'.")


def read(path: str) -> TextureMap:
    """Reads and checks a textures.json. Raises TexturesError for a file that can't be read or isn't valid."""
    try:
        data = read_json(path)
    except ProjectError as error:
        raise TexturesError(str(error)) from None
    if not isinstance(data, dict) or data.get("formatVersion") != FORMAT_VERSION:
        raise TexturesError(f"{path} is not a textures file of format {FORMAT_VERSION}.")
    unknown = set(data) - {"formatVersion", "materials", "meshes"}
    if unknown:
        raise TexturesError(f"{path} has keys this version doesn't know: {', '.join(sorted(unknown))}.")
    try:
        materials = {name: Material(value["shader"], dict(value.get("slots", {})))
                     for name, value in data.get("materials", {}).items()}
        meshes = {mesh_id: MeshEntry(value["meshName"], value["material"])
                  for mesh_id, value in data.get("meshes", {}).items()}
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise TexturesError(f"{path} is malformed: {error!r}.") from None
    texture_map = TextureMap(materials, meshes)
    try:
        check(texture_map)
    except TexturesError as error:
        raise TexturesError(f"{path}: {error}") from None
    return texture_map


def write(path: str, texture_map: TextureMap) -> None:
    """Checks the map and writes it, sorted so a diff shows only what changed."""
    check(texture_map)
    write_json(path, {
        "formatVersion": FORMAT_VERSION,
        "materials": {name: {"shader": material.shader, "slots": dict(sorted(material.slots.items()))}
                      for name, material in sorted(texture_map.materials.items())},
        "meshes": {mesh_id: {"meshName": entry.name, "material": entry.material}
                   for mesh_id, entry in sorted(texture_map.meshes.items())},
    })
