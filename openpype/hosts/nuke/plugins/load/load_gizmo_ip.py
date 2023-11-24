import nuke
import six

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
    create_backdrop,
    get_avalon_knob_data,
    set_avalon_knob_data,
    swap_node_with_dependency,
)
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)


class LoadGizmoInputProcess(load.LoaderPlugin):
    """Loading colorspace soft effect exported from nukestudio"""

    families = ["gizmo"]
    representations = ["*"]
    extensions = {"nk"}

    label = "Load Gizmo - Input Process"
    order = 0
    icon = "eye"
    color = "#cc0000"
    node_color = "0x7533c1ff"

    def load(self, context, name, namespace, data):
        """
        Loading function to get Gizmo as Input Process on viewer

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

            # try to place it under Viewer1
            if not self.connect_active_viewer(group_node):
                nuke.delete(group_node)
                return

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

    def connect_active_viewer(self, group_node):
        """
        Finds Active viewer and
        place the node under it, also adds
        name of group into Input Process of the viewer

        Arguments:
            group_node (nuke node): nuke group node object

        """
        group_node_name = group_node["name"].value()

        viewer = [n for n in nuke.allNodes() if "Viewer1" in n["name"].value()]
        if len(viewer) > 0:
            viewer = viewer[0]
        else:
            msg = str("Please create Viewer node before you "
                      "run this action again")
            self.log.error(msg)
            nuke.message(msg)
            return None

        # get coordinates of Viewer1
        xpos = viewer["xpos"].value()
        ypos = viewer["ypos"].value()

        ypos += 150

        viewer["ypos"].setValue(ypos)

        # set coordinates to group node
        group_node["xpos"].setValue(xpos)
        group_node["ypos"].setValue(ypos + 50)

        # add group node name to Viewer Input Process
        viewer["input_process_node"].setValue(group_node_name)

        # put backdrop under
        create_backdrop(
            label="Input Process",
            layer=2,
            nodes=[viewer, group_node],
            color="0x7c7faaff"
        )

        return True

    def get_item(self, data, trackIndex, subTrackIndex):
        return {key: val for key, val in data.items()
                if subTrackIndex == val["subTrackIndex"]
                if trackIndex == val["trackIndex"]}

    def byteify(self, input):
        """
        Converts unicode strings to strings
        It goes through all dictionary

        Arguments:
            input (dict/str): input

        Returns:
            dict: with fixed values and keys

        """

        if isinstance(input, dict):
            return {self.byteify(key): self.byteify(value)
                    for key, value in input.items()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, six.text_type):
            return str(input)
        else:
            return input

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = container["node"]
        with viewer_update_and_undo_stop():
            nuke.delete(node)
