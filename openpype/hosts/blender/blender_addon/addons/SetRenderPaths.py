import bpy
import logging
import os
import subprocess
from enum import Enum
from pathlib import Path

from libs import paths, templates


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


bl_info = {
    "name": "Render Playblast",
    "description": "Render sequences of images + video, with OpenGL, from viewport or camera view",
    "author": "Quad",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "category": "Render",
    "location": "View 3D > UI",
}

class NodesNames(Enum):
    RENDER_LAYERS = 'R_LAYERS'
    OUTPUT_FILE = 'OUTPUT_FILE'


def get_render_folderpath():
    return templates.get_render_node_output_path()


def set_global_output_path(create_directory=False):
    bpy.context.scene.render.filepath = templates.get_render_global_output_path()
    log.info(f"Global output path has been set to '{bpy.context.scene.render.filepath}'")
    if create_directory:
        Path(bpy.context.scene.render.filepath).mkdir(parents=True, exist_ok=True)
        log.info(f"Folder at path '{bpy.context.scene.render.filepath}' has been created.")


def set_render_nodes_output_path():
    for output_node in [node for node in bpy.context.scene.node_tree.nodes if node.type == NodesNames.OUTPUT_FILE.value]:
        render_node = _browse_render_nodes(output_node.inputs)
        render_layer_name = render_node.layer
        render_node_output_path = templates.get_render_node_output_path(render_layer_name=render_layer_name)

        output_node.base_path = render_node_output_path
        log.info(f"File output path has been set to '{output_node.base_path}'.")


def _browse_render_nodes(nodes_inputs):
    node_links = list()
    for nodes_input in nodes_inputs:
        node_links.extend(nodes_input.links)

    for node_link in node_links:
        target_node = node_link.from_node
        if target_node.type == NodesNames.RENDER_LAYERS.value:
            return target_node

        target_node = _browse_render_nodes(target_node.inputs)
        if target_node: return target_node


class VIEW3D_PT_set_render_paths(bpy.types.Panel):
    bl_label = "Set Render Paths"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quad"


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.operator('setpaths.render', text="Set Render Paths")
        col.operator('setpaths.open', text="Open Last Render Folder")


class OBJECT_OT_set_paths(bpy.types.Operator):
    bl_idname = "setpaths.render"
    bl_label = "Set Render Path"


    def execute(self, context):
        set_global_output_path(create_directory=True)
        set_render_nodes_output_path()

        return {'FINISHED'}


class OBJECT_OT_open_render_folder(bpy.types.Operator):
    bl_idname = "setpaths.open"
    bl_label = "Open Last Render Folder"

    def execute(self, context):
        latest_render_folderpath = paths.get_version_folder_fullpath(
            get_render_folderpath()
        )

        if not latest_render_folderpath or not latest_render_folderpath.exists():
            self.report({'ERROR'}, "File '{}' not found".format(latest_render_folderpath))
            return {'CANCELLED'}

        subprocess.Popen('explorer "' + str(latest_render_folderpath.resolve()) + '"', shell=True)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(VIEW3D_PT_set_render_paths)
    bpy.utils.register_class(OBJECT_OT_set_paths)
    bpy.utils.register_class(OBJECT_OT_open_render_folder)



def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_set_render_paths)
    bpy.utils.unregister_class(OBJECT_OT_set_paths)
    bpy.utils.unregister_class(OBJECT_OT_open_render_folder)
