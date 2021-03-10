from avalon import api, io
from avalon.nuke import lib as anlib
from avalon.nuke import containerise
import nuke


class AlembicPointcacheLoader(api.Loader):
    """
    This will load alembic pointcache into script.
    """

    families = ["pointcache"]
    representations = ["abc"]

    label = "Load Alembic Pointcache"
    icon = "code-fork"
    color = "orange"
    node_color = "0x3469ffff"

    def create_read_geo(self, object_name, file, fps):
        node = nuke.createNode(
            "ReadGeo2", "name {} file {}".format(object_name, file)
        )
        node.forceValidate()
        node["frame_rate"].setValue(float(fps))

        # Ensure all items are imported and selected.
        scene_view = node['scene_view']
        scene_view.setImportedItems(scene_view.getAllItems())
        scene_view.setSelectedItems(scene_view.getAllItems())

        return node

    def load(self, context, name, namespace, data):
        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        fps = version_data.get("fps") or nuke.root()["fps"].getValue()
        namespace = namespace or context['asset']['name']
        # Adding "1" to the end will encourage Nuke to increment this number
        # for multiple instances of the pointcache.
        object_name = "{}_{}_1".format(name, namespace)

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

        with anlib.maintained_selection():
            node = self.create_read_geo(object_name, file, fps)
            node_name = node.name()

            # workaround because nuke's bug is not adding
            # animation keys properly
            xpos = node.xpos()
            ypos = node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(node)
            nuke.nodePaste("%clipboard%")
            node = nuke.toNode(node_name)
            node.setXYpos(xpos, ypos)

        # color node by correct color by actual version
        self.node_version_color(version, node)

        return containerise(
            node=node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__,
            data=data_imprint
        )

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
        # get main variables
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        fps = version_data.get("fps") or nuke.root()["fps"].getValue()
        file = api.get_representation_path(representation).replace("\\", "/")
        object_name = container['objectName']

        old_node = nuke.toNode(object_name)
        xpos = old_node.xpos()
        ypos = old_node.ypos()
        dependencies = old_node.dependencies()

        dependent_connections = []
        for dependent in old_node.dependent():
            for index in range(0, dependent.inputs()):
                connected_node = dependent.input(index)
                if connected_node == old_node:
                    dependent_connections.append(
                        {"input": index, "node": dependent}
                    )

        nuke.delete(old_node)

        # Need to re-create node cause that is only way to avoid the pop-up
        # dialog for importing.
        node = self.create_read_geo(object_name, file, fps)
        node.setXYpos(xpos, ypos)

        # link to original input nodes
        for i, input in enumerate(dependencies):
            node.setInput(i, input)

        for connection in dependent_connections:
            connection["node"].setInput(connection["input"], node)

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["source", "author", "fps"]

        data_imprint = {
            "representation": str(representation["_id"]),
            "frameStart": first,
            "frameEnd": last,
            "version": vname,
            "objectName": object_name
        }

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        node["frame_rate"].setValue(float(fps))

        # color node by correct color by actual version
        self.node_version_color(version, node)

        # Containerise node because its been re-created.
        version = io.find_one({"_id": representation["parent"]})
        subset = io.find_one({"_id": version["parent"]})
        asset = io.find_one({"_id": subset["parent"]})
        project = io.find_one({"_id": asset["parent"]})
        context = {
            "project": project,
            "asset": asset,
            "subset": subset,
            "version": version,
            "representation": representation
        }
        containerise(
            node=node,
            name=container["name"],
            namespace=container["namespace"],
            context=context,
            loader=self.__class__.__name__,
            data=data_imprint
        )

    def node_version_color(self, version, node):
        """ Coloring a node by correct color by actual version
        """
        # get all versions in list
        versions = io.find({
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
        from avalon.nuke import viewer_update_and_undo_stop
        node = nuke.toNode(container['objectName'])
        with viewer_update_and_undo_stop():
            nuke.delete(node)
