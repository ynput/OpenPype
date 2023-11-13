# -*- coding: utf-8 -*-
"""Creator for Unreal Static Meshes."""
from openpype.hosts.houdini.api import plugin
from openpype.lib import BoolDef, EnumDef

import hou


class CreateStaticMesh(plugin.HoudiniCreator):
    """Static Meshes as FBX. """

    identifier = "io.openpype.creators.houdini.staticmesh.fbx"
    label = "Static Mesh (FBX)"
    family = "staticMesh"
    icon = "fa5s.cubes"

    default_variants = ["Main"]

    def create(self, subset_name, instance_data, pre_create_data):

        instance_data.update({"node_type": "filmboxfbx"})

        instance = super(CreateStaticMesh, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        # get the created rop node
        instance_node = hou.node(instance.get("instance_node"))

        # prepare parms
        output_path = hou.text.expandString(
            "$HIP/pyblish/{}.fbx".format(subset_name)
        )

        parms = {
            "startnode": self.get_selection(),
            "sopoutput": output_path,
            # vertex cache format
            "vcformat": pre_create_data.get("vcformat"),
            "convertunits": pre_create_data.get("convertunits"),
            # set render range to use frame range start-end frame
            "trange": 1,
            "createsubnetroot": pre_create_data.get("createsubnetroot")
        }

        # set parms
        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.objNodeTypeCategory(),
            hou.sopNodeTypeCategory()
        ]

    def get_pre_create_attr_defs(self):
        """Add settings for users. """

        attrs = super(CreateStaticMesh, self).get_pre_create_attr_defs()
        createsubnetroot = BoolDef("createsubnetroot",
                                   tooltip="Create an extra root for the "
                                           "Export node when it's a "
                                           "subnetwork. This causes the "
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

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        """
        The default subset name templates for Unreal include {asset} and thus
        we should pass that along as dynamic data.
        """
        dynamic_data = super(CreateStaticMesh, self).get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["asset"] = asset_doc["name"]
        return dynamic_data

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
