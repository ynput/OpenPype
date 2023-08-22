# -*- coding: utf-8 -*-
"""Creator plugin for creating fbx.

It was made to pratice publish process.

Filmbox by default expects an ObjNode
however, we set the sop node explictly
to eleminate any confusion.

This creator by default will select
the output sop with mimimum idx
or the node with render flag isntead.

This plugin is part of publish process guide.
"""

from openpype.hosts.houdini.api import plugin
from openpype.lib import EnumDef

import hou


class CreateFilmboxFBX(plugin.HoudiniCreator):
    """Filmbox FBX Driver."""

    # you should set
    identifier = "io.openpype.creators.houdini.filmboxfbx"
    label = "Filmbox FBX"
    family = "filmboxfbx"
    icon = "fa5s.cubes"

    # optional to set
    default_variant = "Main"
    default_variants = ["Main", "Test"]

    # Overrides HoudiniCreator.create()
    def create(self, subset_name, instance_data, pre_create_data):

        # set node type
        instance_data.update({"node_type": "filmboxfbx"})

        # create instance (calls HoudiniCreator.create())
        instance = super(CreateFilmboxFBX, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        # get the created node
        instance_node = hou.node(instance.get("instance_node"))

        # get parms
        parms = self.get_parms(subset_name, pre_create_data)

        # set parms
        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    # Overrides HoudiniCreator.get_network_categories()
    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.sopNodeTypeCategory()
        ]

    # Overrides HoudiniCreator.get_pre_create_attr_defs()
    def get_pre_create_attr_defs(self):
        attrs = super().get_pre_create_attr_defs()
        vcformat = EnumDef("vcformat",
                           items={
                               0: "Maya Compatible (MC)",
                               1: "3DS MAX Compatible (PC2)"
                                 },
                           default=0,
                           label="Vertex Cache Format")
        trange = EnumDef("trange",
                         items={
                             0: "Render Current Frame",
                             1: "Render Frame Range"
                             },
                             default=0,
                             label="Valid Frame Range")

        return attrs + [vcformat, trange]

    def get_parms(self, subset_name, pre_create_data):
        """Get parameters values for this specific node."""

        # 1. get output path
        output_path = hou.text.expandString(
            "$HIP/pyblish/{}.fbx".format(subset_name))

        # 2. get selection
        selection = self.get_selection()

        # 3. get Vertex Cache Format
        vcformat = pre_create_data.get("vcformat")

        # 4. get Valid Frame Range
        trange = pre_create_data.get("trange")

        # parms dictionary
        parms = {
            "startnode": selection,
            "sopoutput": output_path,
            "vcformat": vcformat,
            "trange": trange
        }

        return parms

    def get_selection(self):
        """Selection Logic.

        how self.selected_nodes should be processed to get
        the desirable node from selection.

        Returns:
            str : node path
        """

        selection = ""

        if self.selected_nodes:
            selected_node = self.selected_nodes[0]

            # Although Houdini allows ObjNode path on `startnode` for the
            # the ROP node we prefer it set to the SopNode path explicitly

            # Allow sop level paths (e.g. /obj/geo1/box1)
            if isinstance(selected_node, hou.SopNode):
                selection = selected_node.path()
                self.log.debug(
                    "Valid SopNode selection, 'Export' in filmboxfbx"
                    " will be set to '%s'."
                    % selected_node
                )

            # Allow object level paths to Geometry nodes (e.g. /obj/geo1)
            # but do not allow other object level nodes types like cameras.
            elif isinstance(selected_node, hou.ObjNode) and \
                    selected_node.type().name() in ["geo"]:

                # get the output node with the minimum
                # 'outputidx' or the node with display flag
                sop_path = self.get_obj_output(selected_node)

                if sop_path:
                    selection = sop_path.path()
                    self.log.debug(
                        "Valid ObjNode selection, 'Export' in filmboxfbx "
                        "will be set to the child path '%s'."
                        % sop_path
                    )

            if not selection:
                self.log.debug(
                    "Selection isn't valid. 'Export' in filmboxfbx will be empty."
                )
        else:
            self.log.debug(
                "No Selection. 'Export' in filmboxfbx will be empty."
            )

        return selection

    def get_obj_output(self, obj_node):
        """Find output node with the smallest 'outputidx'
        or return tje node with the render flag instead.
        """

        outputs = obj_node.subnetOutputs()

        # if obj_node is empty
        if not outputs:
            return

        # if obj_node has one output child whether its
        # sop output node or a node with the render flag
        elif len(outputs) == 1:
            return outputs[0]

        # if there are more than one, then it have multiple ouput nodes
        # return the one with the minimum 'outputidx'
        else:
            return min(outputs,
                       key=lambda node: node.evalParm('outputidx'))
