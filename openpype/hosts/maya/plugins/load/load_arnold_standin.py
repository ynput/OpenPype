import os
import clique

import maya.cmds as cmds

from openpype.settings import get_project_settings
from openpype.pipeline import (
    load,
    legacy_io,
    get_representation_path
)
from openpype.hosts.maya.api.lib import (
    unique_namespace,
    get_attribute_input,
    maintained_selection,
    convert_to_maya_fps
)
from openpype.hosts.maya.api.pipeline import containerise


def is_sequence(files):
    sequence = False
    collections, remainder = clique.assemble(files, minimum_items=1)
    if collections:
        sequence = True
    return sequence


def get_current_session_fps():
    session_fps = float(legacy_io.Session.get('AVALON_FPS', 25))
    return convert_to_maya_fps(session_fps)


class ArnoldStandinLoader(load.LoaderPlugin):
    """Load as Arnold standin"""

    families = [
        "ass",
        "assProxy",
        "animation",
        "model",
        "proxyAbc",
        "pointcache",
        "usd"
    ]
    representations = ["ass", "abc", "usda", "usdc", "usd"]

    label = "Load as Arnold standin"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, options):
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa")
            # Create defaultArnoldRenderOptions before creating aiStandin
            # which tries to connect it. Since we load the plugin and directly
            # create aiStandin without the defaultArnoldRenderOptions,
            # we need to create the render options for aiStandin creation.
            from mtoa.core import createOptions
            createOptions()

        import mtoa.ui.arnoldmenu

        version = context['version']
        version_data = version.get("data", {})

        self.log.info("version_data: {}\n".format(version_data))

        asset = context['asset']['name']
        namespace = namespace or unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        # Set color.
        settings = get_project_settings(context["project"]["name"])
        color = settings['maya']['load']['colors'].get('ass')
        if color is not None:
            cmds.setAttr(root + ".useOutlinerColor", True)
            cmds.setAttr(
                root + ".outlinerColor", color[0], color[1], color[2]
            )

        with maintained_selection():
            # Create transform with shape
            transform_name = label + "_standin"

            standin_shape = mtoa.ui.arnoldmenu.createStandIn()
            standin = cmds.listRelatives(standin_shape, parent=True)[0]
            standin = cmds.rename(standin, transform_name)
            standin_shape = cmds.listRelatives(standin, shapes=True)[0]

            cmds.parent(standin, root)

            # Set the standin filepath
            repre_path = self.filepath_from_context(context)
            path, operator = self._setup_proxy(
                standin_shape, repre_path, namespace
            )
            cmds.setAttr(standin_shape + ".dso", path, type="string")
            sequence = is_sequence(os.listdir(os.path.dirname(repre_path)))
            cmds.setAttr(standin_shape + ".useFrameExtension", sequence)

            fps = version["data"].get("fps") or get_current_session_fps()
            cmds.setAttr(standin_shape + ".abcFPS", float(fps))

        nodes = [root, standin, standin_shape]
        if operator is not None:
            nodes.append(operator)
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def get_next_free_multi_index(self, attr_name):
        """Find the next unconnected multi index at the input attribute."""
        for index in range(10000000):
            connection_info = cmds.connectionInfo(
                "{}[{}]".format(attr_name, index),
                sourceFromDestination=True
            )
            if len(connection_info or []) == 0:
                return index

    def _get_proxy_path(self, path):
        basename_split = os.path.basename(path).split(".")
        proxy_basename = (
            basename_split[0] + "_proxy." + ".".join(basename_split[1:])
        )
        proxy_path = "/".join([os.path.dirname(path), proxy_basename])
        return proxy_basename, proxy_path

    def _update_operators(self, string_replace_operator, proxy_basename, path):
        cmds.setAttr(
            string_replace_operator + ".match",
            proxy_basename.split(".")[0],
            type="string"
        )
        cmds.setAttr(
            string_replace_operator + ".replace",
            os.path.basename(path).split(".")[0],
            type="string"
        )

    def _setup_proxy(self, shape, path, namespace):
        proxy_basename, proxy_path = self._get_proxy_path(path)

        options_node = "defaultArnoldRenderOptions"
        merge_operator = get_attribute_input(options_node + ".operator")
        if merge_operator is None:
            merge_operator = cmds.createNode("aiMerge")
            cmds.connectAttr(
                merge_operator + ".message", options_node + ".operator"
            )

        merge_operator = merge_operator.split(".")[0]

        string_replace_operator = cmds.createNode(
            "aiStringReplace", name=namespace + ":string_replace_operator"
        )
        node_type = "alembic" if path.endswith(".abc") else "procedural"
        cmds.setAttr(
            string_replace_operator + ".selection",
            "*.(@node=='{}')".format(node_type),
            type="string"
        )
        self._update_operators(string_replace_operator, proxy_basename, path)

        cmds.connectAttr(
            string_replace_operator + ".out",
            "{}.inputs[{}]".format(
                merge_operator,
                self.get_next_free_multi_index(merge_operator + ".inputs")
            )
        )

        # We setup the string operator no matter whether there is a proxy or
        # not. This makes it easier to update since the string operator will
        # always be created. Return original path to use for standin.
        if not os.path.exists(proxy_path):
            return path, string_replace_operator

        return proxy_path, string_replace_operator

    def update(self, container, representation):
        # Update the standin
        members = cmds.sets(container['objectName'], query=True)
        for member in members:
            if cmds.nodeType(member) == "aiStringReplace":
                string_replace_operator = member

            shapes = cmds.listRelatives(member, shapes=True)
            if not shapes:
                continue
            if cmds.nodeType(shapes[0]) == "aiStandIn":
                standin = shapes[0]

        path = get_representation_path(representation)
        proxy_basename, proxy_path = self._get_proxy_path(path)

        # Whether there is proxy or not, we still update the string operator.
        # If no proxy exists, the string operator won't replace anything.
        self._update_operators(string_replace_operator, proxy_basename, path)

        dso_path = path
        if os.path.exists(proxy_path):
            dso_path = proxy_path
        cmds.setAttr(standin + ".dso", dso_path, type="string")

        sequence = is_sequence(os.listdir(os.path.dirname(path)))
        cmds.setAttr(standin + ".useFrameExtension", sequence)

        cmds.setAttr(
            container["objectName"] + ".representation",
            str(representation["_id"]),
            type="string"
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
