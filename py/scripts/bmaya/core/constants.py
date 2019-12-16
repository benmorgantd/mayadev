import os

import bmaya.rigging.templates

TEMPLATES_PATH = os.path.abspath(bmaya.rigging.templates.__file__)

ASSET_TYPES = ['prop', 'environment', 'character']
ROOT_JOINT = 'root_00_M_JNT'