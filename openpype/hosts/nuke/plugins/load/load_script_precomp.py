import nuke

from openpype.client import (
    get_version_by_id,
    get_last_version_by_subset_id,
)
from openpype.pipeline import (
    get_current_project_name,
    load,
    get_representation_path,
)
from openpype.hosts.nuke.api.lib import get_avalon_knob_data
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)


class LinkAsGroup(load.LoaderPlugin):
    """Copy the published file to be pasted at the desired location"""

    families = ["workfile", "nukenodes"]
    representations = ["*"]
    extensions = {"nk"}

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

        file = self.filepath_from_context(context).replace("\\", "/")
        self.log.info("file: {}\n".format(file))

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

        # group context is set to precomp, so back up one level.
        nuke.endGroup()

        # P = nuke.nodes.LiveGroup("file {}".format(file))
        P = nuke.createNode(
            "Precomp",
            "file {}".format(file),
            inpanel=False
        )

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
        node = container["node"]

        root = get_representation_path(representation).replace("\\", "/")

        # Get start frame from version data
        project_name = get_current_project_name()
        version_doc = get_version_by_id(project_name, representation["parent"])
        last_version_doc = get_last_version_by_subset_id(
            project_name, version_doc["parent"], fields=["_id"]
        )

        updated_dict = {}
        version_data = version_doc["data"]
        updated_dict.update({
            "representation": str(representation["_id"]),
            "frameEnd": version_data.get("frameEnd"),
            "version": version_doc.get("name"),
            "colorspace": version_data.get("colorspace"),
            "source": version_data.get("source"),
            "fps": version_data.get("fps"),
            "author": version_data.get("author")
        })

        # Update the imprinted representation
        update_container(
            node,
            updated_dict
        )

        node["file"].setValue(root)

        # change color of node
        if version_doc["_id"] == last_version_doc["_id"]:
            color_value = "0xff0ff0ff"
        else:
            color_value = "0xd84f20ff"
        node["tile_color"].setValue(int(color_value, 16))

        self.log.info("updated to version: {}".format(version_doc.get("name")))

    def remove(self, container):
        node = container["node"]
        with viewer_update_and_undo_stop():
            nuke.delete(node)
