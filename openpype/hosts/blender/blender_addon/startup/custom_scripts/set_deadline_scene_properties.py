import sys
import bpy
import os
from bpy.app.handlers import persistent
import argparse
import re
import logging


RENDER_LAYERS = 'R_LAYERS'
OUTPUT_NODE = 'OUTPUT_FILE'


def register():
    bpy.app.handlers.save_pre.append(set_render_nodes_output_path)
    bpy.types.Scene.output_path = bpy.props.StringProperty('/tmp/')
    bpy.types.Scene.render_layer_path = bpy.props.StringProperty('/tmp/')


def unregister():
    bpy.app.handlers.save_pre.remove(set_render_nodes_output_path)
    del bpy.types.Scene.output_path
    del bpy.types.Scene.render_layer_path


def retrieve_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-layer-path", help="Default render layer output path for render")
    parser.add_argument("--output-path", help="Default output path for render")
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


def set_render_nodes_output_path(blender_file_path):
    version = _extract_version_number_from_filepath(blender_file_path)

    bpy.context.scene.render.filepath = bpy.context.scene.output_path

    for output_node in [node for node in bpy.context.scene.node_tree.nodes if node.type == OUTPUT_NODE]:
        render_node = _browse_render_nodes(output_node.inputs)
        render_layer_name = render_node.layer
        output_node.base_path = bpy.context.scene.render_layer_path.format(
            render_layer_name=render_layer_name,
            version = version
        ) + '_'
        logging.info(f"Output node {output_node.name} path has been set to '{output_node.base_path}'.")


def _browse_render_nodes(nodes_inputs):
    node_links = list()
    for nodes_input in nodes_inputs:
        node_links.extend(nodes_input.links)

    for node_link in node_links:
        target_node = node_link.from_node
        if target_node.type == RENDER_LAYERS:
            return target_node
        else:
            target_node = _browse_render_nodes(target_node.inputs)
            if target_node: return target_node


def _extract_version_number_from_filepath(filepath):
    version_regex = r'[^a-zA-Z\d](v\d{3})[^a-zA-Z\d]'
    results = re.search(version_regex, filepath)
    return results.groups()[-1]


def set_cycles_engine():
    bpy.context.scene.render.engine = 'CYCLES'
    logging.info(f"Render engine has been set to {bpy.context.scene.render.engine}")


register()
retrieve_args()
set_cycles_engine()
