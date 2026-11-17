"""Assets on disk: ids, projects, the file model, the registry and local version copies.

Plain Python with no Maya import, so it runs in mayapy, batch jobs and tools outside Maya. Maya save and
load handlers live in bmaya.maya.assethandlers. The design is RigModules' design/asset-model.md (D29, D54): an
asset holds skeletons, rigs and looks.

    from bmaya.core.asset import Asset, Registry

    hero = Asset("shooter\\main\\characters\\hero")
    hero.path("shapes", "body")                               # where the body rig's shape file lives
    hero.path("weights", "winter")                            # where the winter look's weights live
    Registry.of(hero.project).find(skeleton=(hero.id, "default"))   # assets with a rig or look on hero's skeleton
"""

from .asset import Asset, AssetError, AssetLook
from .assetid import AssetIdError
from .project import Project, ProjectError, projects_root
from .records import LookRecord, RecordError, RigRecord, RigRef, SkeletonRef
from .registry import Registry

__all__ = ["Asset", "AssetError", "AssetIdError", "AssetLook", "LookRecord", "Project", "ProjectError", "RecordError", "Registry",
           "RigRecord", "RigRef", "SkeletonRef", "projects_root"]
