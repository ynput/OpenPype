import sys
import bpy
from bpy.app.handlers import persistent
import argparse
import logging


def register():
    bpy.app.handlers.depsgraph_update_post.append(set_output_path)
    bpy.types.Scene.render_extension = bpy.props.StringProperty(
        default=bpy.context.scene.render.image_settings.file_format
    )


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(set_output_path)
    del bpy.types.Scene.render_extension


def execute():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", help="Default output path for render")
    args, unknown = parser.parse_known_args(
        sys.argv[sys.argv.index("--") + 1 :]
    )

    bpy.context.scene.render.filepath = args.output_path + '.' + \
        bpy.context.scene.render.image_settings.file_format
    logging.info(f"Default render filepath has been set to '{bpy.context.scene.render.filepath}'")


@persistent
def set_output_path(scene, depsgraph):
    blender_file_extension = bpy.context.scene.render.image_settings.file_format
    memorized_file_extension = bpy.context.scene.render_extension

    if blender_file_extension != memorized_file_extension:
        bpy.context.scene.render_extension = blender_file_extension
        output_path = bpy.context.scene.render.filepath
        bpy.context.scene.render.filepath = output_path.replace(
            memorized_file_extension, blender_file_extension
        )
        logging.info(
            f"Newer extension has been selected. Output path has been automatically updated. " \
            f"Render filepath is now set to '{bpy.context.scene.render.filepath}'"
        )

register()
execute()
