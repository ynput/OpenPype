import os
import clique

import maya.cmds as cmds
import mtoa.ui.arnoldmenu

from openpype.settings import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)
import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.plugin import get_reference_node
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    unique_namespace
)
from openpype.hosts.maya.api.pipeline import containerise


def is_sequence(files):
    sequence = False
    collections, remainder = clique.assemble(files)
    if collections:
        sequence = True

    return sequence


def set_color(node, context):
    project_name = context["project"]["name"]
    settings = get_project_settings(project_name)
    colors = settings['maya']['load']['colors']
    color = colors.get('ass')
    if color is not None:
        cmds.setAttr(node + ".useOutlinerColor", True)
        cmds.setAttr(
            node + ".outlinerColor", color[0], color[1], color[2]
        )


class AssProxyLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Load Arnold Proxy as reference"""

    families = ["ass"]
    representations = ["ass"]

    label = "Reference .ASS standin with Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, options):
        version = context['version']
        version_data = version.get("data", {})

        self.log.info("version_data: {}\n".format(version_data))

        frame_start = version_data.get("frame_start", None)

        with maintained_selection():

            groupName = "{}:{}".format(namespace, name)
            path = self.fname
            proxy_path_base = os.path.splitext(path)[0]

            if frame_start is not None:
                proxy_path_base = os.path.splitext(proxy_path_base)[0]

                publish_folder = os.path.split(path)[0]
                files_in_folder = os.listdir(publish_folder)
                collections, remainder = clique.assemble(files_in_folder)

                if collections:
                    hashes = collections[0].padding * '#'
                    coll = collections[0].format('{head}[index]{tail}')
                    filename = coll.replace('[index]', hashes)

                    path = os.path.join(publish_folder, filename)

            proxy_path = proxy_path_base + ".ma"
            msg = proxy_path + " does not exist."
            assert os.path.exists(proxy_path), msg

            nodes = cmds.file(
                proxy_path,
                namespace=namespace,
                reference=True,
                returnNewNodes=True,
                groupReference=True,
                groupName=groupName
            )

            cmds.makeIdentity(
                groupName, apply=False, rotate=True, translate=True, scale=True
            )

            # Set attributes
            proxy_shape = cmds.ls(nodes, type="mesh")[0]

            cmds.setAttr(
                proxy_shape + ".aiTranslator", "procedural", type="string"
            )
            cmds.setAttr(proxy_shape + ".dso", self.fname, type="string")
            cmds.setAttr(proxy_shape + ".aiOverrideShaders", 0)

            set_color(groupName, context)

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        node = container["objectName"]

        representation["context"].pop("frame", None)
        path = get_representation_path(representation)
        proxy_path = os.path.splitext(path)[0] + ".ma"

        # Get reference node from container members
        members = cmds.sets(node, query=True, nodesOnly=True)
        reference_node = get_reference_node(members)

        assert os.path.exists(proxy_path), "%s does not exist." % proxy_path

        try:
            file_url = self.prepare_root_value(proxy_path,
                                               representation["context"]
                                                             ["project"]
                                                             ["name"])
            content = cmds.file(file_url,
                                loadReference=reference_node,
                                type="mayaAscii",
                                returnNewNodes=True)

            # Set attributes
            proxy_shape = cmds.ls(content, type="mesh")[0]

            cmds.setAttr(
                proxy_shape + ".aiTranslator", "procedural", type="string"
            )
            cmds.setAttr(proxy_shape + ".dso", self.fname, type="string")
            cmds.setAttr(proxy_shape + ".aiOverrideShaders", 0)

        except RuntimeError as exc:
            # When changing a reference to a file that has load errors the
            # command will raise an error even if the file is still loaded
            # correctly (e.g. when raising errors on Arnold attributes)
            # When the file is loaded and has content, we consider it's fine.
            if not cmds.referenceQuery(reference_node, isLoaded=True):
                raise

            content = cmds.referenceQuery(reference_node,
                                          nodes=True,
                                          dagPath=True)
            if not content:
                raise

            self.log.warning("Ignoring file read error:\n%s", exc)

        # Add new nodes of the reference to the container
        cmds.sets(content, forceElement=node)

        # Remove any placeHolderList attribute entries from the set that
        # are remaining from nodes being removed from the referenced file.
        members = cmds.sets(node, query=True)
        invalid = [x for x in members if ".placeHolderList" in x]
        if invalid:
            cmds.sets(invalid, remove=node)

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")


class AssStandinLoader(load.LoaderPlugin):
    """Load .ASS file as standin"""

    families = ["ass"]
    representations = ["ass"]

    label = "Load .ASS file as standin"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, options):
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

        set_color(root, context)

        # Create transform with shape
        transform_name = label + "_ASS"

        standinShape = mtoa.ui.arnoldmenu.createStandIn()
        standin = cmds.listRelatives(standinShape, parent=True)[0]
        standin = cmds.rename(standin, transform_name)
        standinShape = cmds.listRelatives(standin, shapes=True)[0]

        cmds.parent(standin, root)

        # Set the standin filepath
        cmds.setAttr(standinShape + ".dso", self.fname, type="string")
        sequence = is_sequence(os.listdir(os.path.dirname(self.fname)))
        cmds.setAttr(standinShape + ".useFrameExtension", sequence)

        nodes = [root, standin]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):
        # Update the standin
        standins = list()
        members = cmds.sets(container['objectName'], query=True)
        for member in members:
            shapes = cmds.listRelatives(member, shapes=True)
            if not shapes:
                continue
            if cmds.nodeType(shapes[0]) == "aiStandIn":
                standins.append(shapes[0])

        path = get_representation_path(representation)
        sequence = is_sequence(os.listdir(os.path.dirname(path)))
        for standin in standins:
            cmds.setAttr(standin + ".dso", path, type="string")
            cmds.setAttr(standin + ".useFrameExtension", sequence)

        cmds.setAttr(
            container["objectName"] + ".representation",
            str(representation["_id"]),
            type="string"
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        import maya.cmds as cmds
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
