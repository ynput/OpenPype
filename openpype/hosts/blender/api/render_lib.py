import os

import bpy

from openpype.settings import get_project_settings
from openpype.pipeline import get_current_project_name


def get_default_render_folder(settings):
    """Get default render folder from blender settings."""

    return (settings["blender"]
                    ["RenderSettings"]
                    ["default_render_image_folder"])


def get_aov_separator(settings):
    """Get aov separator from blender settings."""

    aov_sep = (settings["blender"]
                       ["RenderSettings"]
                       ["aov_separator"])

    if aov_sep == "dash":
        return "-"
    elif aov_sep == "underscore":
        return "_"
    elif aov_sep == "dot":
        return "."
    else:
        raise ValueError(f"Invalid aov separator: {aov_sep}")


def get_image_format(settings):
    """Get image format from blender settings."""

    return (settings["blender"]
                    ["RenderSettings"]
                    ["image_format"])


def get_multilayer(settings):
    """Get multilayer from blender settings."""

    return (settings["blender"]
                    ["RenderSettings"]
                    ["multilayer_exr"])


def get_render_product(output_path, name, aov_sep):
    """
    Generate the path to the render product. Blender interprets the `#`
    as the frame number, when it renders.

    Args:
        file_path (str): The path to the blender scene.
        render_folder (str): The render folder set in settings.
        file_name (str): The name of the blender scene.
        instance (pyblish.api.Instance): The instance to publish.
        ext (str): The image format to render.
    """
    filepath = os.path.join(output_path, name)
    render_product = f"{filepath}{aov_sep}beauty.####"
    render_product = render_product.replace("\\", "/")

    return render_product


def set_render_format(ext, multilayer):
    # Set Blender to save the file with the right extension
    bpy.context.scene.render.use_file_extension = True

    image_settings = bpy.context.scene.render.image_settings

    if ext == "exr":
        image_settings.file_format = (
            "OPEN_EXR_MULTILAYER" if multilayer else "OPEN_EXR")
    elif ext == "bmp":
        image_settings.file_format = "BMP"
    elif ext == "rgb":
        image_settings.file_format = "IRIS"
    elif ext == "png":
        image_settings.file_format = "PNG"
    elif ext == "jpeg":
        image_settings.file_format = "JPEG"
    elif ext == "jp2":
        image_settings.file_format = "JPEG2000"
    elif ext == "tga":
        image_settings.file_format = "TARGA"
    elif ext == "tif":
        image_settings.file_format = "TIFF"


def set_render_passes(settings):
    aov_list = (settings["blender"]
                        ["RenderSettings"]
                        ["aov_list"])

    custom_passes = (settings["blender"]
                             ["RenderSettings"]
                             ["custom_passes"])

    vl = bpy.context.view_layer

    vl.use_pass_combined = "combined" in aov_list
    vl.use_pass_z = "z" in aov_list
    vl.use_pass_mist = "mist" in aov_list
    vl.use_pass_normal = "normal" in aov_list
    vl.use_pass_diffuse_direct = "diffuse_light" in aov_list
    vl.use_pass_diffuse_color = "diffuse_color" in aov_list
    vl.use_pass_glossy_direct = "specular_light" in aov_list
    vl.use_pass_glossy_color = "specular_color" in aov_list
    vl.eevee.use_pass_volume_direct = "volume_light" in aov_list
    vl.use_pass_emit = "emission" in aov_list
    vl.use_pass_environment = "environment" in aov_list
    vl.use_pass_shadow = "shadow" in aov_list
    vl.use_pass_ambient_occlusion = "ao" in aov_list

    cycles = vl.cycles

    cycles.denoising_store_passes = "denoising" in aov_list
    cycles.use_pass_volume_direct = "volume_direct" in aov_list
    cycles.use_pass_volume_indirect = "volume_indirect" in aov_list

    aovs_names = [aov.name for aov in vl.aovs]
    for cp in custom_passes:
        cp_name = cp[0]
        if cp_name not in aovs_names:
            aov = vl.aovs.add()
            aov.name = cp_name
        else:
            aov = vl.aovs[cp_name]
        aov.type = cp[1].get("type", "VALUE")

    return aov_list, custom_passes


def set_node_tree(output_path, name, aov_sep, ext, multilayer):
    # Set the scene to use the compositor node tree to render
    bpy.context.scene.use_nodes = True

    tree = bpy.context.scene.node_tree

    # Get the Render Layers node
    rl_node = None
    for node in tree.nodes:
        if node.bl_idname == "CompositorNodeRLayers":
            rl_node = node
            break

    # If there's not a Render Layers node, we create it
    if not rl_node:
        rl_node = tree.nodes.new("CompositorNodeRLayers")

    # Get the enabled output sockets, that are the active passes for the
    # render.
    # We also exclude some layers.
    exclude_sockets = ["Image", "Alpha", "Noisy Image"]
    passes = [
        socket
        for socket in rl_node.outputs
        if socket.enabled and socket.name not in exclude_sockets
    ]

    # Remove all output nodes
    for node in tree.nodes:
        if node.bl_idname == "CompositorNodeOutputFile":
            tree.nodes.remove(node)

    # Create a new output node
    output = tree.nodes.new("CompositorNodeOutputFile")

    image_settings = bpy.context.scene.render.image_settings
    output.format.file_format = image_settings.file_format

    # In case of a multilayer exr, we don't need to use the output node,
    # because the blender render already outputs a multilayer exr.
    if ext == "exr" and multilayer:
        output.layer_slots.clear()
        return []

    output.file_slots.clear()
    output.base_path = output_path

    aov_file_products = []

    # For each active render pass, we add a new socket to the output node
    # and link it
    for render_pass in passes:
        filepath = f"{name}{aov_sep}{render_pass.name}.####"

        output.file_slots.new(filepath)

        aov_file_products.append(
            (render_pass.name, os.path.join(output_path, filepath)))

        node_input = output.inputs[-1]

        tree.links.new(render_pass, node_input)

    return aov_file_products


def imprint_render_settings(node, data):
    RENDER_DATA = "render_data"
    if not node.get(RENDER_DATA):
        node[RENDER_DATA] = {}
    for key, value in data.items():
        if value is None:
            continue
        node[RENDER_DATA][key] = value


def prepare_rendering(asset_group):
    name = asset_group.name

    filepath = bpy.data.filepath
    assert filepath, "Workfile not saved. Please save the file first."

    file_path = os.path.dirname(filepath)
    file_name = os.path.basename(filepath)
    file_name, _ = os.path.splitext(file_name)

    project = get_current_project_name()
    settings = get_project_settings(project)

    render_folder = get_default_render_folder(settings)
    aov_sep = get_aov_separator(settings)
    ext = get_image_format(settings)
    multilayer = get_multilayer(settings)

    set_render_format(ext, multilayer)
    aov_list, custom_passes = set_render_passes(settings)

    output_path = os.path.join(file_path, render_folder, file_name)

    render_product = get_render_product(output_path, name, aov_sep)
    aov_file_product = set_node_tree(
        output_path, name, aov_sep, ext, multilayer)

    bpy.context.scene.render.filepath = render_product

    render_settings = {
        "render_folder": render_folder,
        "aov_separator": aov_sep,
        "image_format": ext,
        "multilayer_exr": multilayer,
        "aov_list": aov_list,
        "custom_passes": custom_passes,
        "render_product": render_product,
        "aov_file_product": aov_file_product,
        "review": True,
    }

    imprint_render_settings(asset_group, render_settings)
