import bpy
import logging
import os
import subprocess
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


def get_view_3D_region():
    return next(iter([area.spaces[0].region_3d for area in bpy.context.screen.areas if area.type == 'VIEW_3D']), None)


def get_render_filepath():
    return templates.get_playblast_path()


def get_renders_types_and_options():
    return {
        "PNG": {
            'extension': '####.png',
        },
        "FFMPEG": {
            'extension': 'mp4',
            'container': 'MPEG4'
        }
    }.items()


class VIEW3D_PT_render_playblast(bpy.types.Panel):
    bl_label = "Render Playblast"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quad"

    use_camera_view: bpy.props.BoolProperty(name="Use Camera View")
    use_transparent_bg: bpy.props.BoolProperty(name="Alpha BG")

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(context.scene, 'use_camera_view')
        col.prop(context.scene, 'use_transparent_bg')
        col.operator('playblast.render', text="Render Playblast")
        col.operator('playblast.open', text="Open Last Playblast Folder")


class OBJECT_OT_render_playblast(bpy.types.Operator):
    bl_idname = "playblast.render"
    bl_label = "Render Playblast"


    def execute(self, context):
        scene = bpy.context.scene
        region = get_view_3D_region()

        use_camera_view = context.scene.use_camera_view
        use_transparent_bg = context.scene.use_transparent_bg

        memorized_render_filepath = scene.render.filepath
        memorized_file_format = scene.render.image_settings.file_format
        memorized_file_extension_use = scene.render.use_file_extension
        if region and use_camera_view:
            memorized_region = region.view_perspective
            region.view_perspective = 'CAMERA'
        scene.render.use_file_extension = False

        render_filepath = get_render_filepath()
        Path(render_filepath).resolve().parent.mkdir(parents=True, exist_ok=True)

        if use_transparent_bg:
            # save current render parameters
            memorized_engine = bpy.context.scene.render.engine
            memorized_film_transparency = bpy.context.scene.render.film_transparent
            memorized_image_settings = bpy.context.scene.render.image_settings.color_mode

            # set scene transparency for alpha in png
            bpy.context.scene.render.engine = 'CYCLES'
            bpy.context.scene.render.film_transparent = True
            bpy.context.scene.render.image_settings.color_mode = 'RGBA'

        for file_format, options in get_renders_types_and_options():
            scene.render.image_settings.file_format = file_format
            scene.render.filepath = render_filepath.format(ext=options['extension'])

            container = options.get('container')
            if container : scene.render.ffmpeg.format = container

            logging.info(f"{'Camera view' if use_camera_view else 'Viewport'} will be rendered at following path : {scene.render.filepath}")

            result = bpy.ops.render.opengl(animation=True)
            if result != {'FINISHED'}:
                logging.error(f'An error has occured when rendering with file_format {file_format} with OpenGL')

        scene.render.filepath = memorized_render_filepath
        scene.render.image_settings.file_format = memorized_file_format
        scene.render.use_file_extension = memorized_file_extension_use
        if region and use_camera_view:
            region.view_perspective = memorized_region

        if use_transparent_bg:
            # reset to memorized parameters for render
            bpy.context.scene.render.engine = memorized_engine
            bpy.context.scene.render.film_transparent = memorized_film_transparency
            bpy.context.scene.render.image_settings.color_mode = memorized_image_settings

        return {'FINISHED'}


class OBJECT_OT_open_playblast_folder(bpy.types.Operator):
    bl_idname = "playblast.open"
    bl_label = "Open Last Playblast Folder"

    def execute(self, context):
        latest_playblast_filepath = paths.get_version_folder_fullpath(
            get_render_filepath()
        )
        if not latest_playblast_filepath or not latest_playblast_filepath.exists():
            self.report({'ERROR'}, "File '{}' not found".format(latest_playblast_filepath))
            return {'CANCELLED'}

        subprocess.Popen(['start', str(latest_playblast_filepath.resolve())], shell=True)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(VIEW3D_PT_render_playblast)
    bpy.utils.register_class(OBJECT_OT_render_playblast)
    bpy.utils.register_class(OBJECT_OT_open_playblast_folder)

    bpy.types.Scene.use_camera_view = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.use_transparent_bg = bpy.props.BoolProperty(default=True)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_render_playblast)
    bpy.utils.unregister_class(OBJECT_OT_render_playblast)
    bpy.utils.unregister_class(OBJECT_OT_open_playblast_folder)

    del bpy.types.Scene.use_camera_view
    del bpy.types.Scene.use_transparent_bg
