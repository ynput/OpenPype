import nuke

from openpype.client import (
    get_version_by_id,
    get_last_version_by_subset_id
)
from openpype.pipeline import (
    load,
    get_current_project_name,
    get_representation_path,
)
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)
from openpype.hosts.nuke.api.lib import (
    maintained_selection
)


class AlembicCameraLoader(load.LoaderPlugin):
    """
    This will load alembic camera into script.
    """

    families = ["camera"]
    representations = ["*"]
    extensions = {"abc"}

    label = "Load Alembic Camera"
    icon = "camera"
    color = "orange"
    node_color = "0x3469ffff"

    def load(self, context, name, namespace, data):
        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        fps = version_data.get("fps") or nuke.root()["fps"].getValue()
        namespace = namespace or context['asset']['name']
        object_name = "{}_{}".format(name, namespace)

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["source", "author", "fps"]

        data_imprint = {"frameStart": first,
                        "frameEnd": last,
                        "version": vname,
                        "objectName": object_name}

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = self.filepath_from_context(context).replace("\\", "/")

        with maintained_selection():
            camera_node = nuke.createNode(
                "Camera2",
                "name {} file {} read_from_file True".format(
                    object_name, file),
                inpanel=False
            )

            camera_node.forceValidate()
            camera_node["frame_rate"].setValue(float(fps))

            # workaround because nuke's bug is not adding
            # animation keys properly
            xpos = camera_node.xpos()
            ypos = camera_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(camera_node)
            nuke.nodePaste("%clipboard%")
            camera_node = nuke.toNode(object_name)
            camera_node.setXYpos(xpos, ypos)

        # color node by correct color by actual version
        self.node_version_color(version, camera_node)

        return containerise(
            node=camera_node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__,
            data=data_imprint)

    def update(self, container, representation):
        """
            Called by Scene Inventory when look should be updated to current
            version.
            If any reference edits cannot be applied, eg. shader renamed and
            material not present, reference is unloaded and cleaned.
            All failed edits are highlighted to the user via message box.

        Args:
            container: object that has look to be updated
            representation: (dict): relationship data to get proper
                                    representation from DB and persisted
                                    data in .json
        Returns:
            None
        """
        # Get version from io
        project_name = get_current_project_name()
        version_doc = get_version_by_id(project_name, representation["parent"])

        object_name = container['objectName']

        # get main variables
        version_data = version_doc.get("data", {})
        vname = version_doc.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        fps = version_data.get("fps") or nuke.root()["fps"].getValue()

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["source", "author", "fps"]

        data_imprint = {"representation": str(representation["_id"]),
                        "frameStart": first,
                        "frameEnd": last,
                        "version": vname,
                        "objectName": object_name}

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = get_representation_path(representation).replace("\\", "/")

        with maintained_selection():
            camera_node = nuke.toNode(object_name)
            camera_node['selected'].setValue(True)

            # collect input output dependencies
            dependencies = camera_node.dependencies()
            dependent = camera_node.dependent()

            camera_node["frame_rate"].setValue(float(fps))
            camera_node["file"].setValue(file)

            # workaround because nuke's bug is
            # not adding animation keys properly
            xpos = camera_node.xpos()
            ypos = camera_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(camera_node)
            nuke.nodePaste("%clipboard%")
            camera_node = nuke.toNode(object_name)
            camera_node.setXYpos(xpos, ypos)

            # link to original input nodes
            for i, input in enumerate(dependencies):
                camera_node.setInput(i, input)
            # link to original output nodes
            for d in dependent:
                index = next((i for i, dpcy in enumerate(
                              d.dependencies())
                              if camera_node is dpcy), 0)
                d.setInput(index, camera_node)

        # color node by correct color by actual version
        self.node_version_color(version_doc, camera_node)

        self.log.info("updated to version: {}".format(version_doc.get("name")))

        return update_container(camera_node, data_imprint)

    def node_version_color(self, version_doc, node):
        """ Coloring a node by correct color by actual version
        """
        # get all versions in list
        project_name = get_current_project_name()
        last_version_doc = get_last_version_by_subset_id(
            project_name, version_doc["parent"], fields=["_id"]
        )

        # change color of node
        if version_doc["_id"] == last_version_doc["_id"]:
            color_value = self.node_color
        else:
            color_value = "0xd88467ff"
        node["tile_color"].setValue(int(color_value, 16))

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = nuke.toNode(container['objectName'])
        with viewer_update_and_undo_stop():
            nuke.delete(node)
