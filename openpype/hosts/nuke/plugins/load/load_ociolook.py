import os
import json
import nuke
import six

from openpype.client import get_version_by_id
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


class LoadOcioLookNodes(load.LoaderPlugin):
    """Loading Ocio look to the nuke node graph"""

    families = ["ociolook"]
    representations = ["*"]
    extensions = {"json"}

    label = "Load OcioLook [nodes]"
    order = 0
    icon = "cc"
    color = "white"
    ignore_attr = ["useLifetime"]

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
            nuke node: containerized nuke node object
        """
        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        root_working_colorspace = nuke.root()["workingSpaceLUT"].value()

        namespace = namespace or context['asset']['name']
        object_name = "{}_{}".format(name, namespace)

        data_imprint = {
            "version": vname,
            "objectName": object_name,
            "source": version_data.get("source", None),
            "author": version_data.get("author", None),
            "fps": version_data.get("fps", None),
        }

        # getting file path
        file = self.filepath_from_context(context)
        print(file)

        dir_path = os.path.dirname(file)
        all_files = os.listdir(dir_path)

        # getting data from json file with unicode conversion
        with open(file, "r") as f:
            json_f = {self.bytify(key): self.bytify(value)
                      for key, value in json.load(f).items()}

        # check if the version in json_f is the same as plugin version
        if json_f["version"] != self.schema_version:
            raise KeyError(
                "Version of json file is not the same as plugin version")

        json_data = json_f["data"]
        ocio_working_colorspace = _colorspace_name_by_type(
            json_data["ocioLookWorkingSpace"])

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
            pre_colorspace = root_working_colorspace
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

            for ocio_item in json_data["ocioLookItems"]:
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

                # TODO: file path from lut representation
                extension = ocio_item["ext"]
                item_lut_file = next(
                    (file for file in all_files if file.endswith(extension)),
                    None
                )
                if not item_lut_file:
                    raise ValueError(
                        "File with extension {} not found in directory".format(
                            extension))

                item_lut_path = os.path.join(
                    dir_path, item_lut_file).replace("\\", "/")
                node["file"].setValue(item_lut_path)
                node["name"].setValue(ocio_item["name"])
                node["direction"].setValue(ocio_item["direction"])
                node["interpolation"].setValue(ocio_item["interpolation"])
                node["working_space"].setValue(input_space)

                node.setInput(0, pre_node)
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

            output = nuke.createNode("Output")
            output.setInput(0, pre_node)

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
        GN = nuke.toNode(container['objectName'])

        file = get_representation_path(representation).replace("\\", "/")
        name = container['name']
        version_data = version_doc.get("data", {})
        vname = version_doc.get("name", None)
        namespace = container['namespace']
        object_name = "{}_{}".format(name, namespace)


    def bytify(self, input):
        """
        Converts unicode strings to strings
        It goes through all dictionary

        Arguments:
            input (dict/str): input

        Returns:
            dict: with fixed values and keys

        """

        if isinstance(input, dict):
            return {self.bytify(key): self.bytify(value)
                    for key, value in input.items()}
        elif isinstance(input, list):
            return [self.bytify(element) for element in input]
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
        pre_node (nuke node): node to connect to
        input_space (str): input colorspace
        output_space (str): output colorspace

    Returns:
        nuke node: node with OCIOColorSpace node
    """
    node = nuke.createNode("OCIOColorSpace")
    node.setInput(0, pre_node)
    node["in_colorspace"].setValue(input_space)
    node["out_colorspace"].setValue(output_space)

    node.setInput(0, pre_node)
    return node
