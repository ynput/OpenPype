import bpy
from bpy.types import Menu, UIList
from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH, BL_TYPE_ICON


def check_type_validity_for_creator(
    datablock: bpy.types.ID, creator_name: str
) -> bool:
    """Check type is valid for creator name.

    Args:
        datablock (bpy.types.ID): Datablock to test type ok.
        creator_name (str): Creator name

    Returns:
        bool: Is datablock type valid for creator
    """
    creator = bpy.context.scene["openpype_creators"].get(creator_name, {})

    return BL_TYPE_DATAPATH.get(type(datablock)) in {
        t[0] for t in creator["bl_types"]
    }


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

        # Publishable switch
        if hasattr(item, "publish"):
            row.prop(item, "publish", text="")

        # Draw name
        row.label(text=item["avalon"]["subset"])


class SCENE_UL_OpenpypeDatablocks(UIList):
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

        # Draw name with icon
        # TODO is it the smartest way to get the icon?
        icon = BL_TYPE_ICON.get(type(item.datablock), "QUESTION")
        if not check_type_validity_for_creator(
            item.datablock, _data["creator_name"]
        ):
            icon = "ERROR"
        row.label(text=item.name, icon=icon)



class SCENE_MT_openpype_instances_context_menu(Menu):
    bl_label = "Vertex Group Specials"

    def draw(self, _context):
        layout = self.layout

        layout.operator("scene.duplicate_openpype_instance", icon='DUPLICATE')


class SCENE_PT_OpenpypeInstancesManager(bpy.types.Panel):
    bl_label = "OpenPype Instances Manager"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        # Check not playing
        if context.screen.is_animation_playing:
            self.layout.label(text="Not available while playing")
            return

        layout = self.layout

        # Exit if no any instance
        if not len(context.scene.openpype_instances):
            layout.operator("scene.create_openpype_instance", icon="ADD")
            return

        row = layout.row()
        ob = context.scene

        # List of OpenPype instances
        row.template_list(
            "SCENE_UL_OpenpypeInstances",
            "",
            ob,
            "openpype_instances",
            ob,
            "openpype_instance_active_index",
            rows=3,
        )

        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("scene.create_openpype_instance", icon="ADD", text="")
        active_instance = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ]
        col.operator(
            "scene.remove_openpype_instance", icon="REMOVE", text=""
        ).instance_name = active_instance.name

        col.separator()

        col.menu("SCENE_MT_openpype_instances_context_menu", icon='DOWNARROW_HLT', text="")

        col.separator()

        # Move buttons
        col.operator(
            "scene.move_openpype_instance", icon="TRIA_UP", text=""
        ).direction = "UP"
        col.operator(
            "scene.move_openpype_instance", icon="TRIA_DOWN", text=""
        ).direction = "DOWN"

        # Draw full name
        col = layout.column(align=True)
        col.prop(active_instance, "name", text="Full name", emboss=False)

        # Icons for accepted types
        subrow = col.row(align=True)
        subrow.label(text="Supported types:")
        for type_icon in active_instance.get("icons", []):
            subrow.label(icon=type_icon)
        subrow.label()  # UI trick


class SCENE_PT_OpenpypeDatablocksManager(bpy.types.Panel):
    bl_label = "OpenPype Instances Manager"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "SCENE_PT_OpenpypeInstancesManager"

    @classmethod
    def poll(cls, context):
        # Don't display if no datablock ref in instance
        return (
            len(context.scene.openpype_instances) > 0
            and not context.screen.is_animation_playing
        )

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        # List of datablocks embeded in instance
        active_openpype_instance = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ]

        # List of datablocks for active instance
        row.template_list(
            "SCENE_UL_OpenpypeDatablocks",
            "",
            active_openpype_instance,
            "datablock_refs",
            active_openpype_instance,
            "datablock_active_index",
            rows=3,
        )

        # Add/Remove datablock to instance
        col = row.column(align=True)
        props = col.operator(
            "scene.add_to_openpype_instance", icon="ADD", text=""
        )
        props.instance_name = active_openpype_instance.name
        props.creator_name = active_openpype_instance["creator_name"]
        if active_openpype_instance.datablock_refs:
            if check_type_validity_for_creator(
                active_openpype_instance.datablock_refs[0].datablock,
                active_openpype_instance["creator_name"],
            ):
                props.datapath = BL_TYPE_DATAPATH.get(
                    type(active_openpype_instance.datablock_refs[0].datablock)
                )

        props = col.operator(
            "scene.remove_from_openpype_instance", icon="REMOVE", text=""
        )
        props.instance_name = active_openpype_instance.name
        props.creator_name = active_openpype_instance["creator_name"]
        if active_openpype_instance.datablock_refs:
            props.datablock_name = active_openpype_instance.datablock_refs[
                active_openpype_instance.datablock_active_index
            ].name

        col.separator()

        # Move buttons
        col.operator(
            "scene.move_openpype_instance_datablock", icon="TRIA_UP", text=""
        ).direction = "UP"
        col.operator(
            "scene.move_openpype_instance_datablock", icon="TRIA_DOWN", text=""
        ).direction = "DOWN"


classes = (
    SCENE_PT_OpenpypeInstancesManager,
    SCENE_PT_OpenpypeDatablocksManager,
    SCENE_UL_OpenpypeInstances,
    SCENE_UL_OpenpypeDatablocks,
    SCENE_MT_openpype_instances_context_menu,
)

register, unregister = bpy.utils.register_classes_factory(classes)
