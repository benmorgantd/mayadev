import maya.cmds as cmds
import maya.api.OpenMaya as om
import json

# TODO: this may be okay reference, generated from Claude, but in the end we need a network node tracking it.

# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------

def _get_matrix(node, attr):
    return om.MMatrix(cmds.getAttr(f"{node}.{attr}"))

def _matrix_to_list(m):
    return [m[i] for i in range(16)]

def _identity_list():
    return _matrix_to_list(om.MMatrix.kIdentity)

def _compute_offset(parent, child):
    """
    offset = child.worldMatrix * parent.worldInverseMatrix
    
    This is the matrix that, when placed in offsetParentMatrix, reproduces
    the child's current world position assuming local TRS is zeroed.
    
    Must be called BEFORE zeroing local TRS and BEFORE making any connections.
    """
    child_world      = _get_matrix(child,  "worldMatrix[0]")
    parent_world_inv = _get_matrix(parent, "worldInverseMatrix[0]")
    return child_world * parent_world_inv


# ---------------------------------------------------------------------------
# Node naming
# ---------------------------------------------------------------------------

def _offset_mm_name(child, i): return f"{child}_matConst_offsetMM{i}"
def _wt_add_name(child):       return f"{child}_matConst_wtAdd"
def _final_mm_name(child):     return f"{child}_matConst_finalMM"


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def matrix_parent_constrain(parents, child, maintain_offset=True, weights=None):
    """
    Matrix parent constraint via offsetParentMatrix. Maya 2020+.

    Evaluation order in Maya:
        worldMatrix = localMatrix * offsetParentMatrix * parentWorldMatrix

    So:
        offsetParentMatrix = desiredWorldMatrix * parentWorldMatrix⁻¹

    The child's local TRS is zeroed before connection to prevent
    double-transformation. If you need local TRS to remain non-zero
    (e.g. an authored translate offset on top), do NOT zero them here
    and instead account for the local matrix in the offset calculation.

    Parameters
    ----------
    parents         : str | list[str]
    child           : str
    maintain_offset : bool
    weights         : list[float] | None   normalised internally by wtAddMatrix

    Returns
    -------
    dict  descriptor (also stored as JSON on final_mm node)
    """
    if isinstance(parents, str):
        parents = [parents]

    n = len(parents)
    if weights is None:
        weights = [1.0 / n] * n
    assert len(weights) == n

    # ------------------------------------------------------------------
    # STEP 1 — snapshot everything BEFORE touching the scene
    #
    # child.worldMatrix is only valid before we zero TRS or make
    # connections, so all offset matrices must be computed first.
    # ------------------------------------------------------------------
    offset_matrices = []
    for par in parents:
        if maintain_offset:
            offset_matrices.append(_compute_offset(par, child))
        else:
            offset_matrices.append(om.MMatrix.kIdentity)

    # ------------------------------------------------------------------
    # STEP 2 — zero local TRS on the child BEFORE connecting anything
    #
    # offsetParentMatrix sits above localMatrix in the chain. If localMatrix
    # is non-identity when we connect, it stacks on top and causes
    # double-transformation and flipping.
    #
    # We only zero unlocked, unconnected, keyable attrs.
    # Scale is left alone — it is not part of offsetParentMatrix's role here
    # and zeroing it would collapse the geometry.
    # ------------------------------------------------------------------
    for ch_attr, values in [("translate", (0, 0, 0)),
                             ("rotate",    (0, 0, 0))]:
        for axis, val in zip("XYZ", values):
            plug = f"{child}.{ch_attr}{axis}"
            locked    = cmds.getAttr(plug, lock=True)
            connected = bool(cmds.listConnections(plug, source=True, destination=False))
            if not locked and not connected:
                cmds.setAttr(plug, val)

    # ------------------------------------------------------------------
    # STEP 3 — build per-parent offset multMatrix nodes
    #
    # matrixIn[0] = baked offset  (static, or identity if no offset)
    # matrixIn[1] = live parent.worldMatrix
    #
    # output = offset * parentWorld
    # ------------------------------------------------------------------
    offset_mms = []
    for i, (par, off_mat) in enumerate(zip(parents, offset_matrices)):
        mm = cmds.createNode("multMatrix", name=_offset_mm_name(child, i))
        cmds.setAttr(mm + ".matrixIn[0]", _matrix_to_list(off_mat), type="matrix")
        cmds.connectAttr(par + ".worldMatrix[0]", mm + ".matrixIn[1]")
        offset_mms.append(mm)

    # ------------------------------------------------------------------
    # STEP 4 — blend layer (wtAddMatrix) for multiple parents
    # ------------------------------------------------------------------
    wt_add       = None
    weight_attrs = []

    if n > 1:
        wt_add = cmds.createNode("wtAddMatrix", name=_wt_add_name(child))
        for i, mm in enumerate(offset_mms):
            cmds.connectAttr(mm + ".matrixSum", f"{wt_add}.wtMatrix[{i}].matrixIn")
            cmds.setAttr(f"{wt_add}.wtMatrix[{i}].weightIn", weights[i])
            weight_attrs.append(f"{wt_add}.wtMatrix[{i}].weightIn")
    else:
        weight_attrs.append(None)

    # ------------------------------------------------------------------
    # STEP 5 — final multMatrix: world → child's parent local space
    #
    # offsetParentMatrix is expressed in the coordinate space of the
    # child's parent node (same as local TRS). Multiplying by
    # child.parentInverseMatrix[0] converts from world space to that space.
    #
    # final = (offset * parentWorld) * childParentInverseWorld
    # ------------------------------------------------------------------
    final_mm = cmds.createNode("multMatrix", name=_final_mm_name(child))

    blend_src = (wt_add + ".matrixSum") if wt_add else (offset_mms[0] + ".matrixSum")
    cmds.connectAttr(blend_src,                          final_mm + ".matrixIn[0]")
    cmds.connectAttr(child + ".parentInverseMatrix[0]",  final_mm + ".matrixIn[1]")

    # ------------------------------------------------------------------
    # STEP 6 — connect to offsetParentMatrix
    # ------------------------------------------------------------------
    cmds.connectAttr(final_mm + ".matrixSum", child + ".offsetParentMatrix")

    # ------------------------------------------------------------------
    # STEP 7 — store descriptor as JSON on the final_mm node
    # ------------------------------------------------------------------
    descriptor = {
        "_type":           "matrixParentConstraint",
        "child":           child,
        "parents":         parents,
        "maintain_offset": maintain_offset,
        "weights":         weights,
        "nodes": {
            "offset_mms": offset_mms,
            "wt_add":     wt_add or "",
            "final_mm":   final_mm,
        },
        "weight_attrs": [a or "" for a in weight_attrs],
    }

    if not cmds.attributeQuery("matConstData", node=final_mm, exists=True):
        cmds.addAttr(final_mm, longName="matConstData", dataType="string")
    cmds.setAttr(final_mm + ".matConstData", json.dumps(descriptor), type="string")

    return descriptor


# ---------------------------------------------------------------------------
# Parse / remove / weight helpers  (unchanged API)
# ---------------------------------------------------------------------------

def parse_matrix_constraint(child):
    conns = cmds.listConnections(
        child + ".offsetParentMatrix",
        source=True, destination=False,
        type="multMatrix",
    )
    if not conns:
        return None
    final_mm = conns[0]
    if not cmds.attributeQuery("matConstData", node=final_mm, exists=True):
        return None
    raw = cmds.getAttr(final_mm + ".matConstData")
    return json.loads(raw) if raw else None


def remove_matrix_constraint(child):
    desc = parse_matrix_constraint(child)
    if desc is None:
        print(f"No matrix constraint found on {child}")
        return
    nodes = desc["nodes"]
    to_kill = (
        [nodes["final_mm"]]
        + ([nodes["wt_add"]] if nodes["wt_add"] else [])
        + nodes["offset_mms"]
    )
    existing = [nd for nd in to_kill if cmds.objExists(nd)]
    if existing:
        cmds.delete(existing)
    if not cmds.listConnections(child + ".offsetParentMatrix", source=True, destination=False):
        cmds.setAttr(child + ".offsetParentMatrix", _identity_list(), type="matrix")


def set_constraint_weight(child, parent_index, value):
    desc = parse_matrix_constraint(child)
    if desc is None:
        raise RuntimeError(f"No matrix constraint found on {child}")
    attr = desc["weight_attrs"][parent_index]
    if not attr:
        raise RuntimeError("Single-parent constraints have no blendable weight attr.")
    cmds.setAttr(attr, value)


def parent_constrain(parent, child, maintain_offset=True):
    if hasattr(parent, "ctrl"): parent = parent.ctrl
    if hasattr(child,  "ctrl"): child  = child.ctrl
    return matrix_parent_constrain([parent], child, maintain_offset=maintain_offset)