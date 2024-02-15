import sys
import bpy
import os
import argparse
import logging


def register():
    bpy.types.Scene.output_path = bpy.props.StringProperty('/tmp/')
    bpy.types.Scene.render_layer_path = bpy.props.StringProperty('/tmp/')
    bpy.types.Scene.playblast_render_path = bpy.props.StringProperty('/tmp/')


def unregister():
    del bpy.types.Scene.output_path
    del bpy.types.Scene.render_layer_path
    del bpy.types.Scene.playblast_render_path


def retrieve_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-layer-path", help="Default render layer output path for render")
    parser.add_argument("--output-path", help="Default output path for render")
    parser.add_argument("--playblast-render-path", help="Default output path for playblasts")
    args, _ = parser.parse_known_args(
        sys.argv[sys.argv.index("--") + 1 :]
    )

    if not args:
        logging.warning(
            f"No arguments found for script {os.path.basename(__file__)}"
        )
        return

    bpy.context.scene.render_layer_path = args.render_layer_path
    bpy.context.scene.output_path = args.output_path.format(
        render_layer_name='_temp'
    )
    bpy.context.scene.playblast_render_path = args.playblast_render_path


register()
retrieve_args()
