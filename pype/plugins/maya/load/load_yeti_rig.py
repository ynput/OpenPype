import os
from collections import defaultdict

from pype.api import config
import pype.hosts.maya.plugin
from pype.hosts.maya import lib


class YetiRigLoader(pype.hosts.maya.plugin.ReferenceLoader):
    """
    This loader will load Yeti rig. You can select something in scene and if it
    has same ID as mesh published with rig, their shapes will be linked
    together.
    """

    families = ["yetiRig"]
    representations = ["ma"]

    label = "Load Yeti Rig"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process_reference(
            self, context, name=None, namespace=None, options=None):

        import maya.cmds as cmds
        from avalon import maya

        # get roots of selected hierarchies
        selected_roots = []
        for sel in cmds.ls(sl=True, long=True):
            selected_roots.append(sel.split("|")[1])

        # get all objects under those roots
        selected_hierarchy = []
        for root in selected_roots:
            selected_hierarchy.append(cmds.listRelatives(
                                      root,
                                      allDescendents=True) or [])

        # flatten the list and filter only shapes
        shapes_flat = []
        for root in selected_hierarchy:
            shapes = cmds.ls(root, long=True, type="mesh") or []
            for shape in shapes:
                shapes_flat.append(shape)

        # create dictionary of cbId and shape nodes
        scene_lookup = defaultdict(list)
        for node in shapes_flat:
            cb_id = lib.get_id(node)
            scene_lookup[cb_id] = node

        # load rig
        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        # for every shape node we've just loaded find matching shape by its
        # cbId in selection. If found outMesh of scene shape will connect to
        # inMesh of loaded shape.
        for destination_node in nodes:
            source_node = scene_lookup[lib.get_id(destination_node)]
            if source_node:
                self.log.info("found: {}".format(source_node))
                self.log.info(
                    "creating connection to {}".format(destination_node))

                cmds.connectAttr("{}.outMesh".format(source_node),
                                 "{}.inMesh".format(destination_node),
                                 force=True)

        groupName = "{}:{}".format(namespace, name)

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']

        c = colors.get('yetiRig')
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])
        self[:] = nodes

        return nodes
