import bpy
from bpy.types import UIList


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
        op_instance = item
        layout.alignment = "CENTER"

        row = layout.row(align=True)
        row.label(text=op_instance.name)

        for type_icon in op_instance["bl_types_icons"]:
            row.label(icon=type_icon)


class ObjectSelectPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_select"
    bl_label = "OpenPype Instances Manager"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

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
        col = row.column(align=True).box()
        col.scale_y = 0.5
        active_openpype_instance = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ]
        for datablock in active_openpype_instance["datablocks"]:
            col.label(text=datablock.name)


classes = (ObjectSelectPanel, SCENE_UL_OpenpypeInstances)

register, unregister = bpy.utils.register_classes_factory(classes)
