"""Assets on disk: ids, projects, the file model, the registry and local version copies.

Plain Python with no Maya import, so it runs in mayapy, batch jobs and tools outside Maya. Maya save and
load handlers live in bmaya.maya.assethandlers. The design is RigModules' design/asset-model.md (D29).

    from bmaya.asset import Asset, Registry

    hero = Asset("shooter\\main\\characters\\hero")
    hero.path("shapes", variant="game")                       # where the game rig's shape file lives
    Registry.of(hero.project).find(skeleton=hero.skeleton)   # assets that can share hero's animation
"""

from .asset import Asset, AssetError
from .assetid import AssetIdError
from .project import Project, ProjectError, projects_root
from .registry import Registry

__all__ = ["Asset", "AssetError", "AssetIdError", "Project", "ProjectError", "Registry", "projects_root"]
