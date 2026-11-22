"""What putting a rig in a look did with each mesh (RigModules D70): the report cmds.setRigLook returns, as data.

Plain Python with no Maya import. A weight file that no longer fits never fails a build, so this is how a mesh that was
folded or bound rigid, or a file saved from another skeleton, is seen. The Asset Editor shows it and Save Skin Weights
clears it: the status is computed by each build and never saved (RigModules D44), so a mesh whose weights were saved
again reads as loaded, and a scene that was never built here has none.

    status = LookStatus.parse(cmds.setRigLook(...))
    status.needs_save                      # True while any mesh was folded, bound rigid or is stale
    status.saved({"B1F3..."})              # the status after that mesh's weights were saved
"""

from __future__ import annotations

import dataclasses
import json

LOADED = "loaded"    # the file's weights as saved
FOLDED = "folded"    # a joint the file names is gone: its weight went to the next skin joint up
RIGID = "rigid"      # the topology changed, or a joint could not be folded: bound whole to the topmost skin joint
RESULTS = (LOADED, FOLDED, RIGID)


@dataclasses.dataclass(frozen=True)
class MeshStatus:
    mesh_id: str
    mesh_name: str
    result: str
    reasons: tuple[str, ...]
    stale_skeleton: bool   # the weight file was saved from another skeleton than the rig's

    @property
    def needs_save(self) -> bool:
        """True when the file on disk no longer says what the scene has: a Save Skin Weights replaces it."""
        return self.result != LOADED or self.stale_skeleton

    @property
    def text(self) -> str:
        """One line for a table cell: the reasons, then the stale mark."""
        parts = list(self.reasons)
        if self.stale_skeleton:
            parts.append("saved from another skeleton")
        return "; ".join(parts)


@dataclasses.dataclass(frozen=True)
class LookStatus:
    look_root: str
    skeleton_stale: bool   # the look's skeleton file is not the rig's (only when setRigLook was given the files)
    meshes: tuple[MeshStatus, ...]

    @classmethod
    def parse(cls, text: str) -> LookStatus:
        """Reads the JSON text cmds.setRigLook returns. Raises ValueError for text that is not a look report."""
        try:
            data = json.loads(text)
            meshes = tuple(MeshStatus(mesh["meshId"], mesh["meshName"], mesh["result"], tuple(mesh["reasons"]),
                                      bool(mesh["staleSkeleton"])) for mesh in data["meshes"])
            return cls(data["lookRoot"], bool(data["skeletonStale"]), meshes)
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"Not a look report ({error}): {text[:80]!r}") from error

    @property
    def needs_save(self) -> bool:
        return self.skeleton_stale or any(mesh.needs_save for mesh in self.meshes)

    @property
    def summary(self) -> str:
        """"3 meshes: 1 loaded, 1 folded, 1 rigid", with the stale count when there is one."""
        counts = [f"{sum(mesh.result == result for mesh in self.meshes)} {result}" for result in RESULTS]
        stale = sum(mesh.stale_skeleton for mesh in self.meshes)
        text = f"{len(self.meshes)} mesh(es): " + ", ".join(counts)
        return text + (f", {stale} stale" if stale else "")

    def saved(self, mesh_ids: set[str]) -> LookStatus:
        """The status once these meshes' weights were saved from the scene: each file now says what the scene has, so
        the mesh reads as loaded. The look's skeleton file is not the saved weights, so skeleton_stale stays until the
        next build."""
        return dataclasses.replace(self, meshes=tuple(
            MeshStatus(mesh.mesh_id, mesh.mesh_name, LOADED, (), False) if mesh.mesh_id in mesh_ids else mesh
            for mesh in self.meshes))
