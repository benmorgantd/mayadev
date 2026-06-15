"""
Keeps track of the last selected rig in the scene, defaulting to the first.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from bmaya.maya.eventsregistry import EventsRegistry, EventType


def get_all_rig_roots():
    """Finds all Rig nodes in the scene by searching for network nodes
    containing a string attribute named 'node' that ends with '_CHAR'.
    """
    rig_roots = []
    it = om.MItDependencyNodes(om.MFn.kAffect)

    while not it.isDone():
        mobj = it.thisNode()
        fn_node = om.MFnDependencyNode(mobj)

        if fn_node.hasAttribute("node"):
            # TODO: we need a stronger identifier string than this
            plug = fn_node.findPlug("node", False)
            try:
                attr_val = plug.asString()
                if attr_val.endswith("_CHAR"):
                    rig_roots.append(fn_node.name())
            except RuntimeError:
                pass
        it.next()

    return rig_roots


def get_rig_root(target):
    """Traverses upward from a given node (string name or MObject) via
    'character' or 'module' plug connections to locate the rig root node.
    """
    if isinstance(target, str):
        if not cmds.objExists(target):
            return None
        sel_list = om.MSelectionList()
        sel_list.add(target)
        current_mobj = sel_list.getDependNode(0)
    elif isinstance(target, om.MObject):
        current_mobj = target
    else:
        return None

    # Resolve DG walk entry point if starting from a physical transform or joint
    if current_mobj.apiType() != om.MFn.kAffect:
        fn_dep = om.MFnDependencyNode(current_mobj)
        connections = fn_dep.getConnections()
        for plug in connections:
            connected_plugs = plug.connectedTo(True, True)
            for conn_plug in connected_plugs:
                node_obj = conn_plug.node()
                if node_obj.apiType() == om.MFn.kAffect:
                    current_mobj = node_obj
                    break
            if current_mobj.apiType() == om.MFn.kAffect:
                break

    # Walk up the dependency hierarchy
    visited = set()
    while current_mobj.apiType() == om.MFn.kAffect:
        fn_dep = om.MFnDependencyNode(current_mobj)
        node_name = fn_dep.name()
        if node_name in visited:
            break
        visited.add(node_name)

        if fn_dep.hasAttribute("node"):
            plug = fn_dep.findPlug("node", False)
            try:
                if plug.asString().endswith("_CHAR"):
                    return node_name
            except RuntimeError:
                pass

        next_mobj = None
        for attr_name in ["character", "module"]:
            if fn_dep.hasAttribute(attr_name):
                plug = fn_dep.findPlug(attr_name, False)
                connected_plugs = plug.connectedTo(True, True)
                if connected_plugs:
                    next_mobj = connected_plugs[0].node()
                    break

        if next_mobj:
            current_mobj = next_mobj
        else:
            break

    return None


# TODO: get node children, get root functions

# TODO: when we adjust all the connections and the structure of our rig we'll need to adjust the tracker and these methods


class ActiveRigTracker(object):
    """Singleton tracker responsible for monitoring and caching the active rig
    using clean public event registration hooks.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ActiveRigTracker, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._active_rig = None
        self._registry = EventsRegistry()

        self.register_callbacks()
        self._initialized = True

        # Initial scan loop for tracking open scene instances immediately
        self.update_from_scene()

    @property
    def active_rig(self):
        """Returns the cached name of the currently active rig root node."""
        return self._active_rig

    def register_callbacks(self):
        """Uses clean public interfaces on the EventsRegistry to establish scene tracking hooks."""
        # Selection Changed Monitoring
        self._registry.add_selection_changed_callback(
            "active_rig_selection_cb", self._on_selection_changed
        )

        # File New Monitoring
        self._registry.add_maya_new_scene_callback(
            "active_rig_scene_new_cb", self._on_scene_changed
        )

        # File Open Monitoring
        self._registry.add_maya_open_scene_callback(
            "active_rig_scene_open_cb", self._on_scene_changed
        )

    def _on_selection_changed(self, *args, **kwargs):
        selection = om.MGlobal.getActiveSelectionList()
        if selection.length() > 0:
            last_selected_mobj = selection.getDependNode(selection.length() - 1)
            rig_root = get_rig_root(last_selected_mobj)
            if rig_root:
                self._active_rig = rig_root

    def _on_scene_changed(self, *args, **kwargs):
        self.update_from_scene()

    def update_from_scene(self):
        """Queries the scene via standalone search metrics to refresh tracking parameters."""
        rigs = get_all_rig_roots()
        if rigs:
            self._active_rig = rigs[0]
        else:
            self._active_rig = None
