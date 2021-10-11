from avalon import api, io
from avalon.nuke import lib as anlib
from avalon.nuke import containerise, update_container
import nuke


class AlembicGeoLoader(api.Loader):
    """
    This will load alembic geo into script.
    """

    families = ["geo"]
    representations = ["abc"]

    label = "Load Alembic Geo"
    icon = "geo"
    color = "orange"
    node_color = "0xff3200ff"

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

        with anlib.maintained_selection():
            geo_node = nuke.createNode(
                "Geo2",
                "name {} file {} read_from_file True".format(
                    object_name, file),
                inpanel=False
            )
            geo_node.forceValidate()
            geo_node["frame_rate"].setValue(float(fps))

            # workaround because nuke's bug is not adding
            # animation keys properly
            xpos = geo_node.xpos()
            ypos = geo_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(geo_node)
            nuke.nodePaste("%clipboard%")
            geo_node = nuke.toNode(object_name)
            geo_node.setXYpos(xpos, ypos)

        # color node by correct color by actual version
        self.node_version_color(version, geo_node)

        return containerise(
            node=geo_node,
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
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })
        object_name = container['objectName']
        # get corresponding node
        geo_node = nuke.toNode(object_name)

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
        file = api.get_representation_path(representation).replace("\\", "/")

        with anlib.maintained_selection():
            geo_node = nuke.toNode(object_name)
            geo_node['selected'].setValue(True)

            # collect input output dependencies
            dependencies = geo_node.dependencies()
            dependent = geo_node.dependent()

            geo_node["frame_rate"].setValue(float(fps))
            geo_node["file"].setValue(file)

            # workaround because nuke's bug is
            # not adding animation keys properly
            xpos = geo_node.xpos()
            ypos = geo_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(geo_node)
            nuke.nodePaste("%clipboard%")
            geo_node = nuke.toNode(object_name)
            geo_node.setXYpos(xpos, ypos)

            # link to original input nodes
            for i, input in enumerate(dependencies):
                geo_node.setInput(i, input)
            # link to original output nodes
            for d in dependent:
                index = next((i for i, dpcy in enumerate(
                              d.dependencies())
                              if geo_node is dpcy), 0)
                d.setInput(index, geo_node)

        # color node by correct color by actual version
        self.node_version_color(version, geo_node)

        self.log.info("udated to version: {}".format(version.get("name")))

        return update_container(geo_node, data_imprint)

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
