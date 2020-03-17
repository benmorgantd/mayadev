import os
import bmaya.rigging.templates

# path to rigging templates
TEMPLATES_PATH = os.path.dirname(os.path.abspath(bmaya.rigging.templates.__file__))

# possible asset types
ASSET_TYPES = ['prop', 'environment', 'character']

# the integer joints and controls start counting up from
COUNT_START = 0
SIDE_NAMES = {'left':'L', 'right':'R', 'middle':'M'}

JOINT_SUFFIX = 'JNT'

ROOT_JOINT = 'root_0{0}_{1}_{2}'.format(COUNT_START, SIDE_NAMES['middle'], JOINT_SUFFIX)

CTRL_SUFFIX = 'ctrl'

# the bottom of the layout stack, which should represent the character's "world" space
TOP_LAYOUT_CONTROL = 'layout_0{0}_{1}_{2}'.format(COUNT_START + 2, SIDE_NAMES['middle'], CTRL_SUFFIX)

MESH_SUFFIX = 'mesh'

