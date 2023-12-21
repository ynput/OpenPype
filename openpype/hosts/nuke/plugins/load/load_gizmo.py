import nuke

from openpype.client import (
    get_version_by_id,
    get_last_version_by_subset_id,
)
from openpype.pipeline import (
    load,
    get_current_project_name,
    get_representation_path,
)
from openpype.hosts.nuke.api.lib import (
    maintained_selection,
    get_avalon_knob_data,
    set_avalon_knob_data,
    swap_node_with_dependency,
)
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)


class LoadGizmo(load.LoaderPlugin):
    """Loading nuke Gizmo"""

    families = ["gizmo"]
    representations = ["*"]
    extensions = {"nk"}

    label = "Load Gizmo"
    order = 0
    icon = "dropbox"
    color = "white"
    node_color = "0x75338eff"

    def load(self, context, name, namespace, data):
        """
        Loading function to get Gizmo into node graph

        Arguments:
            context (dict): context of version
            name (str): name of the version
            namespace (str): asset name
            data (dict): compulsory attribute > not used

        Returns:
            nuke node: containerized nuke node object
        """

        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        namespace = namespace or context['asset']['name']
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["frameStart", "frameEnd", "handleStart", "handleEnd",
                    "source", "author", "fps"]

        data_imprint = {
            "frameStart": first,
            "frameEnd": last,
            "version": vname,
            "colorspaceInput": colorspace
        }

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = self.filepath_from_context(context).replace("\\", "/")

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        with maintained_selection():
            # add group from nk
            nuke.nodePaste(file)

            group_node = nuke.selectedNode()

            group_node["name"].setValue(object_name)

            return containerise(
                node=group_node,
                name=name,
                namespace=namespace,
                context=context,
                loader=self.__class__.__name__,
                data=data_imprint)

    def update(self, container, representation):
        """Update the Loader's path

        Nuke automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """

        # get main variables
        # Get version from io
        project_name = get_current_project_name()
        version_doc = get_version_by_id(project_name, representation["parent"])

        # get corresponding node
        group_node = container["node"]

        file = get_representation_path(representation).replace("\\", "/")
        name = container['name']
        version_data = version_doc.get("data", {})
        vname = version_doc.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        namespace = container['namespace']
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        add_keys = ["frameStart", "frameEnd", "handleStart", "handleEnd",
                    "source", "author", "fps"]

        data_imprint = {
            "representation": str(representation["_id"]),
            "frameStart": first,
            "frameEnd": last,
            "version": vname,
            "colorspaceInput": colorspace
        }

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # capture pipeline metadata
        avalon_data = get_avalon_knob_data(group_node)

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        with maintained_selection([group_node]):
            # insert nuke script to the script
            nuke.nodePaste(file)
            # convert imported to selected node
            new_group_node = nuke.selectedNode()
            # swap nodes with maintained connections
            with swap_node_with_dependency(
                    group_node, new_group_node) as node_name:
                new_group_node["name"].setValue(node_name)
                # set updated pipeline metadata
                set_avalon_knob_data(new_group_node, avalon_data)

        last_version_doc = get_last_version_by_subset_id(
            project_name, version_doc["parent"], fields=["_id"]
        )

        # change color of node
        if version_doc["_id"] == last_version_doc["_id"]:
            color_value = self.node_color
        else:
            color_value = "0xd88467ff"

        new_group_node["tile_color"].setValue(int(color_value, 16))

        self.log.info("updated to version: {}".format(version_doc.get("name")))

        return update_container(new_group_node, data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = container["node"]
        with viewer_update_and_undo_stop():
            nuke.delete(node)
