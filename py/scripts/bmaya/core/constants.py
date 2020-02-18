import os
import bmaya.rigging.rigTemplates

TEMPLATES_PATH = os.path.dirname(os.path.abspath(bmaya.rigging.rigTemplates.__file__))

ASSET_TYPES = ['prop', 'environment', 'character']
ROOT_JOINT = 'root_00_M_JNT'