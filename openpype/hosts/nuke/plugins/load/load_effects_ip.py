import json
from collections import OrderedDict
import six
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
from openpype.hosts.nuke.api import lib
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)


class LoadEffectsInputProcess(load.LoaderPlugin):
    """Loading colorspace soft effect exported from nukestudio"""

    families = ["effect"]
    representations = ["*"]
    extensions = {"json"}

    label = "Load Effects - Input Process"
    order = 0
    icon = "eye"
    color = "#cc0000"
    ignore_attr = ["useLifetime"]

    def load(self, context, name, namespace, data):
        """
        Loading function to get the soft effects to particular read node

        Arguments:
            context (dict): context of version
            name (str): name of the version
            namespace (str): asset name
            data (dict): compulsory attribute > not used

        Returns:
            nuke node: containerised nuke node object
        """

        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        workfile_first_frame = int(nuke.root()["first_frame"].getValue())
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
            "colorspaceInput": colorspace,
        }

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = self.filepath_from_context(context).replace("\\", "/")

        # getting data from json file with unicode conversion
        with open(file, "r") as f:
            json_f = {self.byteify(key): self.byteify(value)
                      for key, value in json.load(f).items()}

        # get correct order of nodes by positions on track and subtrack
        nodes_order = self.reorder_nodes(json_f)

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        GN = nuke.createNode(
            "Group",
            "name {}_1".format(object_name),
            inpanel=False
        )

        # adding content to the group node
        with GN:
            pre_node = nuke.createNode("Input")
            pre_node["name"].setValue("rgb")

            for _, ef_val in nodes_order.items():
                node = nuke.createNode(ef_val["class"])
                for k, v in ef_val["node"].items():
                    if k in self.ignore_attr:
                        continue

                    try:
                        node[k].value()
                    except NameError as e:
                        self.log.warning(e)
                        continue

                    if isinstance(v, list) and len(v) > 4:
                        node[k].setAnimated()
                        for i, value in enumerate(v):
                            if isinstance(value, list):
                                for ci, cv in enumerate(value):
                                    node[k].setValueAt(
                                        cv,
                                        (workfile_first_frame + i),
                                        ci)
                            else:
                                node[k].setValueAt(
                                    value,
                                    (workfile_first_frame + i))
                    else:
                        node[k].setValue(v)

                node.setInput(0, pre_node)
                pre_node = node

            output = nuke.createNode("Output")
            output.setInput(0, pre_node)

        # try to place it under Viewer1
        if not self.connect_active_viewer(GN):
            nuke.delete(GN)
            return

        GN["tile_color"].setValue(int("0x3469ffff", 16))

        self.log.info("Loaded lut setup: `{}`".format(GN["name"].value()))

        return containerise(
            node=GN,
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
        GN = container["node"]

        file = get_representation_path(representation).replace("\\", "/")
        version_data = version_doc.get("data", {})
        vname = version_doc.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        workfile_first_frame = int(nuke.root()["first_frame"].getValue())
        colorspace = version_data.get("colorspace", None)

        add_keys = ["frameStart", "frameEnd", "handleStart", "handleEnd",
                    "source", "author", "fps"]

        data_imprint = {
            "representation": str(representation["_id"]),
            "frameStart": first,
            "frameEnd": last,
            "version": vname,
            "colorspaceInput": colorspace,
        }

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # Update the imprinted representation
        update_container(
            GN,
            data_imprint
        )

        # getting data from json file with unicode conversion
        with open(file, "r") as f:
            json_f = {self.byteify(key): self.byteify(value)
                      for key, value in json.load(f).items()}

        # get correct order of nodes by positions on track and subtrack
        nodes_order = self.reorder_nodes(json_f)

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        # adding content to the group node
        with GN:
            # first remove all nodes
            [nuke.delete(n) for n in nuke.allNodes()]

            # create input node
            pre_node = nuke.createNode("Input")
            pre_node["name"].setValue("rgb")

            for _, ef_val in nodes_order.items():
                node = nuke.createNode(ef_val["class"])
                for k, v in ef_val["node"].items():
                    if k in self.ignore_attr:
                        continue

                    try:
                        node[k].value()
                    except NameError as e:
                        self.log.warning(e)
                        continue

                    if isinstance(v, list) and len(v) > 4:
                        node[k].setAnimated()
                        for i, value in enumerate(v):
                            if isinstance(value, list):
                                for ci, cv in enumerate(value):
                                    node[k].setValueAt(
                                        cv,
                                        (workfile_first_frame + i),
                                        ci)
                            else:
                                node[k].setValueAt(
                                    value,
                                    (workfile_first_frame + i))
                    else:
                        node[k].setValue(v)
                node.setInput(0, pre_node)
                pre_node = node

            # create output node
            output = nuke.createNode("Output")
            output.setInput(0, pre_node)

        # get all versions in list
        last_version_doc = get_last_version_by_subset_id(
            project_name, version_doc["parent"], fields=["_id"]
        )

        # change color of node
        if version_doc["_id"] == last_version_doc["_id"]:
            color_value = "0x3469ffff"
        else:
            color_value = "0xd84f20ff"
        GN["tile_color"].setValue(int(color_value, 16))

        self.log.info("updated to version: {}".format(version_doc.get("name")))

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
        lib.create_backdrop(
            label="Input Process",
            layer=2,
            nodes=[viewer, group_node],
            color="0x7c7faaff")

        return True

    def reorder_nodes(self, data):
        new_order = OrderedDict()
        trackNums = [v["trackIndex"] for k, v in data.items()
                     if isinstance(v, dict)]
        subTrackNums = [v["subTrackIndex"] for k, v in data.items()
                        if isinstance(v, dict)]

        for trackIndex in range(
                min(trackNums), max(trackNums) + 1):
            for subTrackIndex in range(
                    min(subTrackNums), max(subTrackNums) + 1):
                item = self.get_item(data, trackIndex, subTrackIndex)
                if item is not {}:
                    new_order.update(item)
        return new_order

    def get_item(self, data, trackIndex, subTrackIndex):
        return {key: val for key, val in data.items()
                if isinstance(val, dict)
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
