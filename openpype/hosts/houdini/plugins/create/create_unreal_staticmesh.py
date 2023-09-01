# -*- coding: utf-8 -*-
"""Creator plugin for creating Unreal Static Meshes.

Unreal Static Meshes will be published as FBX.

Filmbox by default expects an ObjNode
however, we set the sop node explictly
to eleminate any confusion.

This will make Filmbox to ignore any object transformations!

get_obj_output selects
the output sop with mimimum idx
or the node with render flag isntead.

This plugin is part of publish process guide.
"""

from openpype.hosts.houdini.api import plugin
from openpype.lib import BoolDef, EnumDef

import hou


class CreateUnrealStaticMesh(plugin.HoudiniCreator):
    """Unreal Static Meshes with collisions. """

    # you should set
    identifier = "io.openpype.creators.houdini.unrealstaticmesh.fbx"
    label = "Unreal - Static Mesh (FBX)"
    family = "staticMesh"
    icon = "fa5s.cubes"

    # optional to set
    default_variant = "Main"
    # 'default_variants' will be overriden by settings.
    default_variants = ["Main", "Test"]

    # Overrides HoudiniCreator.create()
    def create(self, subset_name, instance_data, pre_create_data):

        # set node type
        instance_data.update({"node_type": "filmboxfbx"})

        # create instance (calls HoudiniCreator.create())
        instance = super(CreateUnrealStaticMesh, self).create(
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
        """Add settings for users. """

        attrs = super().get_pre_create_attr_defs()
        createsubnetroot = BoolDef("createsubnetroot",
                                     tooltip="Create an extra root for the Export node "
                                             "when it’s a subnetwork. This causes the "
                                             "exporting subnetwork node to be "
                                             "represented in the FBX file.",
                                     default=False,
                                     label="Create Root for Subnet")
        vcformat = EnumDef("vcformat",
                           items={
                               0: "Maya Compatible (MC)",
                               1: "3DS MAX Compatible (PC2)"
                           },
                           default=0,
                           label="Vertex Cache Format")
        convert_units = BoolDef("convertunits",
                                tooltip="When on, the FBX is converted"
                                        "from the current Houdini "
                                        "system units to the native "
                                        "FBX unit of centimeters.",
                                default=False,
                                label="Convert Units")

        return attrs + [createsubnetroot, vcformat, convert_units]

    # Overrides BaseCreator.get_dynamic_data()
    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        """
        The default subset name templates for Unreal include {asset} and thus
        we should pass that along as dynamic data.
        """
        dynamic_data = super(CreateUnrealStaticMesh, self).get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["asset"] = asset_doc["name"]
        return dynamic_data

    def get_parms(self, subset_name, pre_create_data):
        """Get parameters values for this specific node."""

        # 1. get output path
        output_path = hou.text.expandString(
            "$HIP/pyblish/{}.fbx".format(subset_name))

        # 2. get selection
        selection = self.get_selection()

        # 3. get Vertex Cache Format
        vcformat = pre_create_data.get("vcformat")

        # 4. get convert_units
        convertunits = pre_create_data.get("convertunits")

        # 5. get Valid Frame Range
        trange = 1

        # 6. get createsubnetroot
        createsubnetroot = pre_create_data.get("createsubnetroot")

        # parms dictionary
        parms = {
            "startnode": selection,
            "sopoutput": output_path,
            "vcformat": vcformat,
            "convertunits": convertunits,
            "trange": trange,
            "createsubnetroot": createsubnetroot
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

            # Accept sop level nodes (e.g. /obj/geo1/box1)
            if isinstance(selected_node, hou.SopNode):
                selection = selected_node.path()
                self.log.debug(
                    "Valid SopNode selection, 'Export' in filmboxfbx"
                    " will be set to '%s'.", selected_node
                )

            # Accept object level nodes (e.g. /obj/geo1)
            elif isinstance(selected_node, hou.ObjNode):
                selection = selected_node.path()
                self.log.debug(
                    "Valid ObjNode selection, 'Export' in filmboxfbx "
                    "will be set to the child path '%s'.", selection
                )

            else:
                self.log.debug(
                    "Selection isn't valid. 'Export' in "
                    "filmboxfbx will be empty."
                )
        else:
            self.log.debug(
                "No Selection. 'Export' in filmboxfbx will be empty."
            )

        return selection
