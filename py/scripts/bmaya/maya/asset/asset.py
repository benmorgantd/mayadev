"""Purpose:
Base class for production Assets that handles logic for asset Id, file management, and versioning.
Assets are made up of components, which are the individual files that make up the asset.
For example, a character asset may have components for model, rig, textures, weights, etc.

Assets are identified by an Id, which is a string in the format: project|type|nameUtils.

The project is the name of the project the asset belongs to, the type is the type of asset (e.g. character, prop, environment),
and the name is the name of the asset itself. The asset class also has methods for opening the asset in the file explorer,
opening the asset file in Maya, referencing the asset file in Maya, checking if an asset exists,
finding files of a certain type within the asset's directory, and versioning the asset.
"""

import os
import shutil
import maya.cmds as cmds
from .components import *
from bmaya.core import constants, log
import bmaya.maya.constants


class Asset(object):
    def __init__(self, asset_id):
        self.asset_id = Asset.validate_id(asset_id)

        self.components = []

    @property
    def root_dir(self):
        root = self.clean_path(
            os.path.join(
                bmaya.maya.constants.RIGGING_PROJECT_DIR,
                self.project,
                self.asset_type,
                self.name,
            )
        )

        if os.path.exists(root):
            return root
        else:
            os.makedirs(root)
            return root

    @property
    def project(self):
        return self.asset_id.split("|")[0]

    @property
    def asset_type(self):
        return self.asset_id.split("|")[1]

    @property
    def name(self):
        return self.asset_id.split("|")[2]
        # test

    @classmethod
    def validate_id(cls, asset_id):
        """Determine if the given id is acceptable.
        Ids should be a string in the format: project|type|name"""

        assert isinstance(asset_id, str)

        if "|" not in asset_id:
            raise ValueError("Id should have tokens split by the pike character.")

        split_id = asset_id.split("|")

        if len(split_id) != 3:
            raise ValueError("Id must be three tokens separated by pikes")

        # check for illegal characters that may cause path errors
        if any(not token.isalnum() for token in split_id):
            raise ValueError("Id is not alphanumeric and contains illegal characters.")

        return asset_id

    @classmethod
    def open_in_explorer(cls, path):
        if os.path.exists(path):
            os.startfile(os.path.dirname(path))

    @classmethod
    def open_file(cls, path):
        if os.path.exists(path):
            if path.endswith(".ma"):
                cmds.file(path, open=True, force=True)
            else:
                os.startfile(path)

    @classmethod
    def reference_file(cls, path):
        if os.path.exists(path):
            if path.endswith(".ma"):
                cmds.file(
                    path,
                    reference=True,
                    namespace=os.path.splitext(os.path.basename(path))[0],
                )

    @classmethod
    def exists(cls, project, name, asset_type):
        """Checks if the given asset exists"""

        root_dir = os.path.abspath(
            os.path.join(
                bmaya.maya.constants.RIGGING_PROJECT_DIR, project, asset_type, name
            )
        )

        if os.path.exists(root_dir):
            return root_dir

        else:
            return False

    @classmethod
    def find_files_of_type(cls, path, filetype):
        if os.path.exists(path):
            return [f for f in os.listdir(path) if f.endswith("." + filetype)]
        else:
            return []

    @classmethod
    def split_path(cls, filepath):
        """split a path into all of its components"""

        result = []

        while os.path.split(filepath)[1]:
            splitname = os.path.split(filepath)
            result.append(splitname[1])
            filepath = splitname[0]

        result.reverse()

        return result

    @classmethod
    def get_asset_id_from_file(cls, filepath):
        """Given a path, derive from it the asset's name, type, and project"""

        filepath = cls.clean_path(filepath)

        asset_name = None
        asset_project = None
        asset_type = None

        dirname = cls.clean_path(os.path.dirname(filepath))
        basename = cls.clean_path(os.path.basename(filepath))

        # see if it's in a subdirectory of PROJECT_ROOT

        for directory, subdirectory, directory_files in os.walk(
            bmaya.maya.constants.RIGGING_PROJECT_DIR
        ):
            if dirname in cls.clean_path(directory) and any(
                basename in cls.clean_path(f) for f in directory_files
            ):
                # this file is within this asset's directory
                root_directory = cls.clean_path(
                    os.path.dirname(
                        os.path.join(
                            bmaya.maya.constants.RIGGING_PROJECT_DIR, "projects"
                        )
                    )
                )
                # returns [project, type, name, ..., basename]
                split_root_relative_path = cls.split_path(
                    filepath.split(root_directory)[1]
                )
                asset_name = split_root_relative_path[2]
                asset_type = split_root_relative_path[1]
                asset_project = split_root_relative_path[0]
        if asset_project and asset_type and asset_name:
            return "|".join([asset_project, asset_type, asset_name])
        else:
            log.warning("NO ASSET FOUND")
            return None

    def component_path_from_type(self, component_type):
        for component in self.components:
            if component.type == component_type:
                return component.full_path

    def version_asset(self):
        """Versions the entire asset to a folder"""

        version_folder = os.path.join(self.root_dir, (self.name + ".Versions"))

        if not os.path.exists(version_folder):
            os.makedirs(version_folder)

        num_versions = len(os.listdir(version_folder))

        # make a new version folder

        version_num = str(num_versions + 1)
        version_num = version_num.zfill(3)

        new_version_folder = os.path.join(version_folder, self.name + version_num)

        log.info("\nCreating asset version " + version_num)

        os.mkdir(new_version_folder)

        for component in self.components:
            component_file = component.full_path

            log.info("Versioning asset component " + component.type)

            if component.type == "weights":
                weights_dir = os.path.join(new_version_folder, "weights")
                os.mkdir(weights_dir)

                weight_files = [
                    os.path.join(component.full_path, f)
                    for f in component.files
                    if f.endswith(".weights")
                ]

                for weight_file in weight_files:
                    shutil.copy(weight_file, weights_dir)

            elif component_file and os.path.exists(component_file):
                shutil.copy(component_file, new_version_folder)

        log.info("\nAsset versioned successfully to: " + new_version_folder)

    @classmethod
    def clean_path(cls, filepath):
        return os.path.abspath(filepath.lower())

    # TODO: add component-loading logic at the asset level?
