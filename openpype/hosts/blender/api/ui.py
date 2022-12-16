import bpy
from bpy.types import UIList
from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH


class SCENE_UL_OpenpypeInstances(UIList):
    def draw_item(
        self,
        _context,
        layout,
        _data,
        item,
        icon,
        _active_data_,
        _active_propname,
        _index,
    ):
        row = layout.row(align=True)

        # Draw name
        row.label(text=item.name)

        # Icons for accepted types
        for type_icon in item.get("icons", []):
            row.label(icon=type_icon)

        row.separator()

        # Publishable switch
        if hasattr(item, "publish"):
            row.prop(item, "publish", text="")


class ObjectSelectPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_select"
    bl_label = "OpenPype Instances Manager"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        # Exit if no any instance
        if not len(context.scene.openpype_instances):
            layout.operator("scene.create_openpype_instance", icon="ADD")
            return

        row = layout.row(align=True)
        ob = context.scene

        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("scene.create_openpype_instance", icon="ADD", text="")
        col.operator(
            "scene.remove_openpype_instance", icon="REMOVE", text=""
        ).instance_name = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ].name

        # List of OpenPype instances
        row.template_list(
            "SCENE_UL_OpenpypeInstances",
            "",
            ob,
            "openpype_instances",
            ob,
            "openpype_instance_active_index",
        )

        row.separator()

        # List of datablocks embeded in instance
        active_openpype_instance = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ]

        # List of datablocks for active instance
        row.template_list(
            "SCENE_UL_OpenpypeInstances",
            "",
            active_openpype_instance,
            "datablock_refs",
            active_openpype_instance,
            "datablock_active_index",
        )

        # Add/Remove datablock to instance
        col = row.column(align=True)
        props = col.operator(
            "scene.add_to_openpype_instance", icon="ADD", text=""
        )
        props.instance_name = active_openpype_instance.name
        props.creator_name = active_openpype_instance["creator_name"]
        props.datapath = BL_TYPE_DATAPATH.get(
            type(active_openpype_instance.datablock_refs[0].datablock)
        )

        props = col.operator(
            "scene.remove_from_openpype_instance", icon="REMOVE", text=""
        )
        props.instance_name = active_openpype_instance.name
        props.creator_name = active_openpype_instance["creator_name"]
        props.datablock_name = active_openpype_instance.datablock_refs[
            active_openpype_instance.datablock_active_index
        ].name


classes = (ObjectSelectPanel, SCENE_UL_OpenpypeInstances)

register, unregister = bpy.utils.register_classes_factory(classes)
