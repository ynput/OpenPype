import os
import json
import secrets
import nuke
import six

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
    viewer_update_and_undo_stop,
    update_container,
)


class LoadOcioLookNodes(load.LoaderPlugin):
    """Loading Ocio look to the nuke.Node graph"""

    families = ["ociolook"]
    representations = ["*"]
    extensions = {"json"}

    label = "Load OcioLook [nodes]"
    order = 0
    icon = "cc"
    color = "white"
    ignore_attr = ["useLifetime"]

    # plugin attributes
    current_node_color = "0x4ecd91ff"
    old_node_color = "0xd88467ff"

    # json file variables
    schema_version = 1

    def load(self, context, name, namespace, data):
        """
        Loading function to get the soft effects to particular read node

        Arguments:
            context (dict): context of version
            name (str): name of the version
            namespace (str): asset name
            data (dict): compulsory attribute > not used

        Returns:
            nuke.Node: containerized nuke.Node object
        """
        namespace = namespace or context['asset']['name']
        suffix = secrets.token_hex(nbytes=4)
        node_name = "{}_{}_{}".format(
            name, namespace, suffix)

        # getting file path
        filepath = self.filepath_from_context(context)

        json_f = self._load_json_data(filepath)

        group_node = self._create_group_node(
            filepath, json_f["data"])
        # renaming group node
        group_node["name"].setValue(node_name)

        self._node_version_color(context["version"], group_node)

        self.log.info(
            "Loaded lut setup: `{}`".format(group_node["name"].value()))

        return containerise(
            node=group_node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__
        )

    def _create_group_node(
        self,
        filepath,
        data,
        group_node=None
    ):
        """Creates group node with all the nodes inside.

        Creating mainly `OCIOFileTransform` nodes with `OCIOColorSpace` nodes
        in between - in case those are needed.

        Arguments:
            filepath (str): path to json file
            data (dict): data from json file
            group_node (Optional[nuke.Node]): group node or None

        Returns:
            nuke.Node: group node with all the nodes inside
        """
        # get corresponding node

        root_working_colorspace = nuke.root()["workingSpaceLUT"].value()

        dir_path = os.path.dirname(filepath)
        all_files = os.listdir(dir_path)

        ocio_working_colorspace = _colorspace_name_by_type(
            data["ocioLookWorkingSpace"])

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        input_node = None
        output_node = None
        if group_node:
            # remove all nodes between Input and Output nodes
            for node in group_node.nodes():
                if node.Class() not in ["Input", "Output"]:
                    nuke.delete(node)
                elif node.Class() == "Input":
                    input_node = node
                elif node.Class() == "Output":
                    output_node = node
        else:
            group_node = nuke.createNode(
                "Group",
                inpanel=False
            )

        # adding content to the group node
        with group_node:
            pre_colorspace = root_working_colorspace

            # reusing input node if it exists during update
            if input_node:
                pre_node = input_node
            else:
                pre_node = nuke.createNode("Input")
                pre_node["name"].setValue("rgb")

            # Compare script working colorspace with ocio working colorspace
            # found in json file and convert to json's if needed
            if pre_colorspace != ocio_working_colorspace:
                pre_node = _add_ocio_colorspace_node(
                    pre_node,
                    pre_colorspace,
                    ocio_working_colorspace
                )
                pre_colorspace = ocio_working_colorspace

            for ocio_item in data["ocioLookItems"]:
                input_space = _colorspace_name_by_type(
                    ocio_item["input_colorspace"])
                output_space = _colorspace_name_by_type(
                    ocio_item["output_colorspace"])

                # making sure we are set to correct colorspace for otio item
                if pre_colorspace != input_space:
                    pre_node = _add_ocio_colorspace_node(
                        pre_node,
                        pre_colorspace,
                        input_space
                    )

                node = nuke.createNode("OCIOFileTransform")

                # file path from lut representation
                extension = ocio_item["ext"]
                item_name = ocio_item["name"]

                item_lut_file = next(
                    (
                        file for file in all_files
                        if file.endswith(extension)
                    ),
                    None
                )
                if not item_lut_file:
                    raise ValueError(
                        "File with extension '{}' not "
                        "found in directory".format(extension)
                    )

                item_lut_path = os.path.join(
                    dir_path, item_lut_file).replace("\\", "/")
                node["file"].setValue(item_lut_path)
                node["name"].setValue(item_name)
                node["direction"].setValue(ocio_item["direction"])
                node["interpolation"].setValue(ocio_item["interpolation"])
                node["working_space"].setValue(input_space)

                pre_node.autoplace()
                node.setInput(0, pre_node)
                node.autoplace()
                # pass output space into pre_colorspace for next iteration
                # or for output node comparison
                pre_colorspace = output_space
                pre_node = node

            # making sure we are back in script working colorspace
            if pre_colorspace != root_working_colorspace:
                pre_node = _add_ocio_colorspace_node(
                    pre_node,
                    pre_colorspace,
                    root_working_colorspace
                )

            # reusing output node if it exists during update
            if not output_node:
                output = nuke.createNode("Output")
            else:
                output = output_node

            output.setInput(0, pre_node)

        return group_node

    def update(self, container, representation):

        project_name = get_current_project_name()
        version_doc = get_version_by_id(project_name, representation["parent"])

        group_node = container["node"]

        filepath = get_representation_path(representation)

        json_f = self._load_json_data(filepath)

        group_node = self._create_group_node(
            filepath,
            json_f["data"],
            group_node
        )

        self._node_version_color(version_doc, group_node)

        self.log.info("Updated lut setup: `{}`".format(
            group_node["name"].value()))

        return update_container(
            group_node, {"representation": str(representation["_id"])})

    def _load_json_data(self, filepath):
        # getting data from json file with unicode conversion
        with open(filepath, "r") as _file:
            json_f = {self._bytify(key): self._bytify(value)
                      for key, value in json.load(_file).items()}

        # check if the version in json_f is the same as plugin version
        if json_f["version"] != self.schema_version:
            raise KeyError(
                "Version of json file is not the same as plugin version")

        return json_f

    def _bytify(self, input):
        """
        Converts unicode strings to strings
        It goes through all dictionary

        Arguments:
            input (dict/str): input

        Returns:
            dict: with fixed values and keys

        """

        if isinstance(input, dict):
            return {self._bytify(key): self._bytify(value)
                    for key, value in input.items()}
        elif isinstance(input, list):
            return [self._bytify(element) for element in input]
        elif isinstance(input, six.text_type):
            return str(input)
        else:
            return input

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = nuke.toNode(container['objectName'])
        with viewer_update_and_undo_stop():
            nuke.delete(node)

    def _node_version_color(self, version, node):
        """ Coloring a node by correct color by actual version"""

        project_name = get_current_project_name()
        last_version_doc = get_last_version_by_subset_id(
            project_name, version["parent"], fields=["_id"]
        )

        # change color of node
        if version["_id"] == last_version_doc["_id"]:
            color_value = self.current_node_color
        else:
            color_value = self.old_node_color
        node["tile_color"].setValue(int(color_value, 16))


def _colorspace_name_by_type(colorspace_data):
    """
    Returns colorspace name by type

    Arguments:
        colorspace_data (dict): colorspace data

    Returns:
        str: colorspace name
    """
    if colorspace_data["type"] == "colorspaces":
        return colorspace_data["name"]
    elif colorspace_data["type"] == "roles":
        return colorspace_data["colorspace"]
    else:
        raise KeyError("Unknown colorspace type: {}".format(
            colorspace_data["type"]))


def _add_ocio_colorspace_node(pre_node, input_space, output_space):
    """
    Adds OCIOColorSpace node to the node graph

    Arguments:
        pre_node (nuke.Node): node to connect to
        input_space (str): input colorspace
        output_space (str): output colorspace

    Returns:
        nuke.Node: node with OCIOColorSpace node
    """
    node = nuke.createNode("OCIOColorSpace")
    node.setInput(0, pre_node)
    node["in_colorspace"].setValue(input_space)
    node["out_colorspace"].setValue(output_space)

    pre_node.autoplace()
    node.setInput(0, pre_node)
    node.autoplace()

    return node
