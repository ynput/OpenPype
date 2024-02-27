import bpy
import logging
import os
import subprocess

from libs import paths


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


bl_info = {
    "name": "Render Playblast",
    "description": "Render sequences of images + video, with OpenGL, from viewport or camera view",
    "author": "Quad",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "category": "Render",
    "location": "View 3D > UI",
}


def get_view_3D_region():
    return next(iter([area.spaces[0].region_3d for area in bpy.context.screen.areas if area.type == 'VIEW_3D']), None)


def get_render_filepath(extension, version):
    return bpy.context.scene.playblast_render_path.format(
        version=version,
        extension=extension
    )


def get_renders_types_and_extensions():
    return {
        "PNG": '####.png',
        "FFMPEG": 'mp4'
    }.items()


class VIEW3D_PT_render_playblast(bpy.types.Panel):
    bl_label = "Render Playblast"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quad"

    use_camera_view: bpy.props.BoolProperty(name="Use Camera View")

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(context.scene, 'use_camera_view')
        col.operator('playblast.render', text="Render Playblast")
        col.operator('playblast.open', text="Open Last Playblast Folder")


class OBJECT_OT_render_playblast(bpy.types.Operator):
    bl_idname = "playblast.render"
    bl_label = "Render Playblast"


    def execute(self, context):
        scene = bpy.context.scene
        region = get_view_3D_region()

        use_camera_view = context.scene.use_camera_view

        memorized_render_filepath = scene.render.filepath
        memorized_file_format = scene.render.image_settings.file_format
        memorized_file_extension_use = scene.render.use_file_extension
        if region and use_camera_view:
            memorized_region = region.view_perspective
            region.view_perspective = 'CAMERA'
        scene.render.use_file_extension = False

        version = paths.get_next_version_folder(bpy.context.scene.playblast_render_path)

        for file_format, file_extension in get_renders_types_and_extensions():
            scene.render.image_settings.file_format = file_format
            scene.render.filepath = get_render_filepath(file_extension, version)
            logging.info(f"{'Camera view' if use_camera_view else 'Viewport'} will be rendered at following path : {scene.render.filepath}")
            result = bpy.ops.render.opengl(animation=True)
            if result != {'FINISHED'}:
                logging.error(f'An error has occured when rendering with file_format {file_format} with OpenGL')

        scene.render.filepath = memorized_render_filepath
        scene.render.image_settings.file_format = memorized_file_format
        scene.render.use_file_extension = memorized_file_extension_use
        if region and use_camera_view:
            region.view_perspective = memorized_region
        return {'FINISHED'}


class OBJECT_OT_open_playblast_folder(bpy.types.Operator):
    bl_idname = "playblast.open"
    bl_label = "Open Last Playblast Folder"

    def execute(self, context):
        playblast_version_folderpath = paths.get_version_folder(bpy.context.scene.playblast_render_path)

        if not playblast_version_folderpath or not os.path.exists(playblast_version_folderpath):
            self.report({'ERROR'}, "File '{}' not found".format(bpy.context.scene.playblast_render_path))
            return {'CANCELLED'}

        subprocess.Popen(['start', playblast_version_folderpath], shell=True)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(VIEW3D_PT_render_playblast)
    bpy.utils.register_class(OBJECT_OT_render_playblast)
    bpy.utils.register_class(OBJECT_OT_open_playblast_folder)

    bpy.types.Scene.use_camera_view = bpy.props.BoolProperty(default=False)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_render_playblast)
    bpy.utils.unregister_class(OBJECT_OT_render_playblast)
    bpy.utils.unregister_class(OBJECT_OT_open_playblast_folder)

    del bpy.types.Scene.use_camera_view
