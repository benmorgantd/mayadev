# possible asset types
ASSET_TYPES = ["prop", "environment", "character", "head"]

# the integer joints and controls start counting up from
COUNT_START = 0

SIDE_NAMES = {"left": "L", "right": "R", "middle": "M"}

JOINT_SUFFIX = "JNT"

DOWN_AXIS = "X"

SPINE_UP_AXIS = "Y"

UP_AXIS = "Y"

ROOT_JOINT = f"root_0{COUNT_START}_{SIDE_NAMES['middle']}_{JOINT_SUFFIX}"

CTRL_SUFFIX = "ctrl"

# the bottom of the layout stack, which should represent the character's
# "world" space
TOP_LAYOUT_CONTROL = (
    f"layout_{str(COUNT_START).zfill(2)}_{SIDE_NAMES['middle']}_{CTRL_SUFFIX}"
)
BOTTOM_LAYOUT_CONTROL = (
    f"layout_{str(COUNT_START + 2).zfill(2)}_{SIDE_NAMES['middle']}_{CTRL_SUFFIX}"
)

MESH_SUFFIX = "mesh"

UNIT_VECTORS = {"X": [1, 0, 0], "Y": [0, 1, 0], "Z": [0, 0, 1]}

LAYOUT_CONTROL_COUNT = 3

MODULE_SUFFIX = "LIMB"
