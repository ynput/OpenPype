import sys
import bpy
from bpy.app.handlers import persistent
import argparse
import re
import logging


RENDER_LAYERS = 'R_LAYERS'
RENDER_LAYER_IMAGE_OUTPUT = 'Image'


def register():
    bpy.app.handlers.save_pre.append(set_render_nodes_output_path)
    bpy.types.Scene.output_path = bpy.props.StringProperty('/tmp/')


def unregister():
    bpy.app.handlers.save_pre.remove(set_render_nodes_output_path)
    del bpy.types.Scene.output_path


def initialize_default_values():
    bpy.context.scene.render.filepath = bpy.context.scene.output_path


def memorize_output_path():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", help="Default output path for render")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :]
    )

    bpy.context.scene.output_path = args.output_path


def set_render_nodes_output_path(blender_file_path):
    version = _extract_version_number_from_filepath(blender_file_path)
    for render_node in [node for node in bpy.context.scene.node_tree.nodes if node.type == RENDER_LAYERS]:
        render_layer_name = render_node.layer
        output_node = render_node.outputs[RENDER_LAYER_IMAGE_OUTPUT].links[0].to_node
        output_node.base_path = bpy.context.scene.output_path.format(
            render_layer_name=render_layer_name,
            version = version
        ) + '_'
        logging.info(f"Output node {output_node.name} path has been set to '{output_node.base_path}'.")


def _extract_version_number_from_filepath(filepath):
    version_regex = r'[^a-zA-Z\d](v\d{3})[^a-zA-Z\d]'
    results = re.search(version_regex, filepath)
    return results.groups()[-1]


def set_cycles_engine():
    bpy.context.scene.render.engine = 'CYCLES'
    logging.info(f"Render engine has been set to {bpy.context.scene.render.engine}")


register()
initialize_default_values()
memorize_output_path()
set_cycles_engine()
