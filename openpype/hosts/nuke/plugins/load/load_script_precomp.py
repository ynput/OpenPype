import nuke
from avalon import api, io

from openpype.hosts.nuke.api.lib import get_avalon_knob_data
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)


class LinkAsGroup(api.Loader):
    """Copy the published file to be pasted at the desired location"""

    representations = ["nk"]
    families = ["workfile", "nukenodes"]

    label = "Load Precomp"
    order = 0
    icon = "file"
    color = "#cc0000"

    def load(self, context, name, namespace, data):
        # for k, v in context.items():
        #     log.info("key: `{}`, value: {}\n".format(k, v))
        version = context['version']
        version_data = version.get("data", {})

        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        file = self.fname.replace("\\", "/")
        self.log.info("file: {}\n".format(self.fname))

        precomp_name = context["representation"]["context"]["subset"]

        self.log.info("versionData: {}\n".format(context["version"]["data"]))

        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["frameStart", "frameEnd", "handleStart", "handleEnd",
                    "source", "author", "fps"]

        data_imprint = {
                "startingFrame": first,
                "frameStart": first,
                "frameEnd": last,
                "version": vname
        }
        for k in add_keys:
            data_imprint.update({k: context["version"]['data'][k]})
        data_imprint.update({"objectName": precomp_name})

        # group context is set to precomp, so back up one level.
        nuke.endGroup()

        # P = nuke.nodes.LiveGroup("file {}".format(file))
        P = nuke.createNode(
            "Precomp",
            "file {}".format(file))

        # Set colorspace defined in version data
        colorspace = context["version"]["data"].get("colorspace", None)
        self.log.info("colorspace: {}\n".format(colorspace))

        P["name"].setValue("{}_{}".format(name, namespace))
        P["useOutput"].setValue(True)

        with P:
            # iterate through all nodes in group node and find pype writes
            writes = [n.name() for n in nuke.allNodes()
                      if n.Class() == "Group"
                      if get_avalon_knob_data(n)]

            if writes:
                # create panel for selecting output
                panel_choices = " ".join(writes)
                panel_label = "Select write node for output"
                p = nuke.Panel("Select Write Node")
                p.addEnumerationPulldown(
                    panel_label, panel_choices)
                p.show()
                P["output"].setValue(p.value(panel_label))

        P["tile_color"].setValue(0xff0ff0ff)

        return containerise(
                     node=P,
                     name=name,
                     namespace=namespace,
                     context=context,
                     loader=self.__class__.__name__,
                     data=data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Update the Loader's path

        Nuke automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """
        node = nuke.toNode(container['objectName'])

        root = api.get_representation_path(representation).replace("\\", "/")

        # Get start frame from version data
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })

        # get all versions in list
        versions = io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        updated_dict = {}
        updated_dict.update({
            "representation": str(representation["_id"]),
            "frameEnd": version["data"].get("frameEnd"),
            "version": version.get("name"),
            "colorspace": version["data"].get("colorspace"),
            "source": version["data"].get("source"),
            "handles": version["data"].get("handles"),
            "fps": version["data"].get("fps"),
            "author": version["data"].get("author")
        })

        # Update the imprinted representation
        update_container(
            node,
            updated_dict
        )

        node["file"].setValue(root)

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd84f20ff", 16))
        else:
            node["tile_color"].setValue(int("0xff0ff0ff", 16))

        self.log.info("updated to version: {}".format(version.get("name")))

    def remove(self, container):
        node = nuke.toNode(container['objectName'])
        with viewer_update_and_undo_stop():
            nuke.delete(node)
