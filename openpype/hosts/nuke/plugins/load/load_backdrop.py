import nuke
import nukescripts

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
    find_free_space_to_paste_nodes,
    maintained_selection,
    reset_selection,
    select_nodes,
    get_avalon_knob_data,
    set_avalon_knob_data
)
from openpype.hosts.nuke.api.command import viewer_update_and_undo_stop
from openpype.hosts.nuke.api import containerise, update_container


class LoadBackdropNodes(load.LoaderPlugin):
    """Loading Published Backdrop nodes (workfile, nukenodes)"""

    families = ["workfile", "nukenodes"]
    representations = ["*"]
    extensions = {"nk"}

    label = "Import Nuke Nodes"
    order = 0
    icon = "eye"
    color = "white"
    node_color = "0x7533c1ff"

    def load(self, context, name, namespace, data):
        """
        Loading function to import .nk file into script and wrap
        it on backdrop

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
        namespace = namespace or context['asset']['name']
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["source", "author", "fps"]

        data_imprint = {
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

        # Get mouse position
        n = nuke.createNode("NoOp")
        xcursor, ycursor = (n.xpos(), n.ypos())
        reset_selection()
        nuke.delete(n)

        bdn_frame = 50

        with maintained_selection():

            # add group from nk
            nuke.nodePaste(file)

            # get all pasted nodes
            new_nodes = list()
            nodes = nuke.selectedNodes()

            # get pointer position in DAG
            xpointer, ypointer = find_free_space_to_paste_nodes(
                nodes, direction="right", offset=200 + bdn_frame
            )

            # reset position to all nodes and replace inputs and output
            for n in nodes:
                reset_selection()
                xpos = (n.xpos() - xcursor) + xpointer
                ypos = (n.ypos() - ycursor) + ypointer
                n.setXYpos(xpos, ypos)

                # replace Input nodes for dots
                if n.Class() in "Input":
                    dot = nuke.createNode("Dot")
                    new_name = n.name().replace("INP", "DOT")
                    dot.setName(new_name)
                    dot["label"].setValue(new_name)
                    dot.setXYpos(xpos, ypos)
                    new_nodes.append(dot)

                    # rewire
                    dep = n.dependent()
                    for d in dep:
                        index = next((i for i, dpcy in enumerate(
                                      d.dependencies())
                                      if n is dpcy), 0)
                        d.setInput(index, dot)

                    # remove Input node
                    reset_selection()
                    nuke.delete(n)
                    continue

                # replace Input nodes for dots
                elif n.Class() in "Output":
                    dot = nuke.createNode("Dot")
                    new_name = n.name() + "_DOT"
                    dot.setName(new_name)
                    dot["label"].setValue(new_name)
                    dot.setXYpos(xpos, ypos)
                    new_nodes.append(dot)

                    # rewire
                    dep = next((d for d in n.dependencies()), None)
                    if dep:
                        dot.setInput(0, dep)

                    # remove Input node
                    reset_selection()
                    nuke.delete(n)
                    continue
                else:
                    new_nodes.append(n)

            # reselect nodes with new Dot instead of Inputs and Output
            reset_selection()
            select_nodes(new_nodes)
            # place on backdrop
            bdn = nukescripts.autoBackdrop()

            # add frame offset
            xpos = bdn.xpos() - bdn_frame
            ypos = bdn.ypos() - bdn_frame
            bdwidth = bdn["bdwidth"].value() + (bdn_frame*2)
            bdheight = bdn["bdheight"].value() + (bdn_frame*2)

            bdn["xpos"].setValue(xpos)
            bdn["ypos"].setValue(ypos)
            bdn["bdwidth"].setValue(bdwidth)
            bdn["bdheight"].setValue(bdheight)

            bdn["name"].setValue(object_name)
            bdn["label"].setValue("Version tracked frame: \n`{}`\n\nPLEASE DO NOT REMOVE OR MOVE \nANYTHING FROM THIS FRAME!".format(object_name))
            bdn["note_font_size"].setValue(20)

            return containerise(
                node=bdn,
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

        name = container['name']
        version_data = version_doc.get("data", {})
        vname = version_doc.get("name", None)
        namespace = container['namespace']
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        add_keys = ["source", "author", "fps"]

        data_imprint = {
            "representation": str(representation["_id"]),
            "version": vname,
            "colorspaceInput": colorspace,
        }

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        with maintained_selection():
            xpos = GN.xpos()
            ypos = GN.ypos()
            avalon_data = get_avalon_knob_data(GN)
            nuke.delete(GN)
            # add group from nk
            nuke.nodePaste(file)

            GN = nuke.selectedNode()
            set_avalon_knob_data(GN, avalon_data)
            GN.setXYpos(xpos, ypos)
            GN["name"].setValue(object_name)

        # get all versions in list
        last_version_doc = get_last_version_by_subset_id(
            project_name, version_doc["parent"], fields=["_id"]
        )

        # change color of node
        if version_doc["_id"] == last_version_doc["_id"]:
            color_value = self.node_color
        else:
            color_value = "0xd88467ff"
        GN["tile_color"].setValue(int(color_value, 16))

        self.log.info("updated to version: {}".format(version_doc.get("name")))

        return update_container(GN, data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        node = container["node"]
        with viewer_update_and_undo_stop():
            nuke.delete(node)
