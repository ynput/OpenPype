import nuke

from openpype.pipeline import (
    legacy_io,
    load,
    get_representation_path,
)
from openpype.hosts.nuke.api.lib import maintained_selection
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)


class AlembicModelLoader(load.LoaderPlugin):
    """
    This will load alembic model or anim into script.
    """

    families = ["model", "pointcache", "animation"]
    representations = ["abc"]

    label = "Load Alembic"
    icon = "cube"
    color = "orange"
    node_color = "0x4ecd91ff"

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
        file = self.fname.replace("\\", "/")

        with maintained_selection():
            model_node = nuke.createNode(
                "ReadGeo2",
                "name {} file {} ".format(
                    object_name, file),
                inpanel=False
            )
            model_node.forceValidate()
            model_node["frame_rate"].setValue(float(fps))

            # workaround because nuke's bug is not adding
            # animation keys properly
            xpos = model_node.xpos()
            ypos = model_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(model_node)
            nuke.nodePaste("%clipboard%")
            model_node = nuke.toNode(object_name)
            model_node.setXYpos(xpos, ypos)

        # color node by correct color by actual version
        self.node_version_color(version, model_node)

        return containerise(
            node=model_node,
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
        version = legacy_io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })
        object_name = container['objectName']
        # get corresponding node
        model_node = nuke.toNode(object_name)

        # get main variables
        version_data = version.get("data", {})
        vname = version.get("name", None)
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
            model_node = nuke.toNode(object_name)
            model_node['selected'].setValue(True)

            # collect input output dependencies
            dependencies = model_node.dependencies()
            dependent = model_node.dependent()

            model_node["frame_rate"].setValue(float(fps))
            model_node["file"].setValue(file)

            # workaround because nuke's bug is
            # not adding animation keys properly
            xpos = model_node.xpos()
            ypos = model_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(model_node)
            nuke.nodePaste("%clipboard%")
            model_node = nuke.toNode(object_name)
            model_node.setXYpos(xpos, ypos)

            # link to original input nodes
            for i, input in enumerate(dependencies):
                model_node.setInput(i, input)
            # link to original output nodes
            for d in dependent:
                index = next((i for i, dpcy in enumerate(
                              d.dependencies())
                              if model_node is dpcy), 0)
                d.setInput(index, model_node)

        # color node by correct color by actual version
        self.node_version_color(version, model_node)

        self.log.info("updated to version: {}".format(version.get("name")))

        return update_container(model_node, data_imprint)

    def node_version_color(self, version, node):
        """ Coloring a node by correct color by actual version
        """
        # get all versions in list
        versions = legacy_io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd88467ff", 16))
        else:
            node["tile_color"].setValue(int(self.node_color, 16))

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = nuke.toNode(container['objectName'])
        with viewer_update_and_undo_stop():
            nuke.delete(node)
