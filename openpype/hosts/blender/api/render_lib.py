from pathlib import Path

import bpy

from openpype import AYON_SERVER_ENABLED
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


def get_renderer(settings):
    """Get renderer from blender settings."""

    return (settings["blender"]
                    ["RenderSettings"]
                    ["renderer"])


def get_compositing(settings):
    """Get compositing from blender settings."""

    return (settings["blender"]
                    ["RenderSettings"]
                    ["compositing"])


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
    filepath = output_path / name.lstrip("/")
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


def set_render_passes(settings, renderer):
    aov_list = set(settings["blender"]["RenderSettings"]["aov_list"])
    custom_passes = settings["blender"]["RenderSettings"]["custom_passes"]

    # Common passes for both renderers
    vl = bpy.context.view_layer

    # Data Passes
    vl.use_pass_combined = "combined" in aov_list
    vl.use_pass_z = "z" in aov_list
    vl.use_pass_mist = "mist" in aov_list
    vl.use_pass_normal = "normal" in aov_list

    # Light Passes
    vl.use_pass_diffuse_direct = "diffuse_light" in aov_list
    vl.use_pass_diffuse_color = "diffuse_color" in aov_list
    vl.use_pass_glossy_direct = "specular_light" in aov_list
    vl.use_pass_glossy_color = "specular_color" in aov_list
    vl.use_pass_emit = "emission" in aov_list
    vl.use_pass_environment = "environment" in aov_list
    vl.use_pass_ambient_occlusion = "ao" in aov_list

    # Cryptomatte Passes
    vl.use_pass_cryptomatte_object = "cryptomatte_object" in aov_list
    vl.use_pass_cryptomatte_material = "cryptomatte_material" in aov_list
    vl.use_pass_cryptomatte_asset = "cryptomatte_asset" in aov_list

    if renderer == "BLENDER_EEVEE":
        # Eevee exclusive passes
        eevee = vl.eevee

        # Light Passes
        vl.use_pass_shadow = "shadow" in aov_list
        eevee.use_pass_volume_direct = "volume_light" in aov_list

        # Effects Passes
        eevee.use_pass_bloom = "bloom" in aov_list
        eevee.use_pass_transparent = "transparent" in aov_list

        # Cryptomatte Passes
        vl.use_pass_cryptomatte_accurate = "cryptomatte_accurate" in aov_list
    elif renderer == "CYCLES":
        # Cycles exclusive passes
        cycles = vl.cycles

        # Data Passes
        vl.use_pass_position = "position" in aov_list
        vl.use_pass_vector = "vector" in aov_list
        vl.use_pass_uv = "uv" in aov_list
        cycles.denoising_store_passes = "denoising" in aov_list
        vl.use_pass_object_index = "object_index" in aov_list
        vl.use_pass_material_index = "material_index" in aov_list
        cycles.pass_debug_sample_count = "sample_count" in aov_list

        # Light Passes
        vl.use_pass_diffuse_indirect = "diffuse_indirect" in aov_list
        vl.use_pass_glossy_indirect = "specular_indirect" in aov_list
        vl.use_pass_transmission_direct = "transmission_direct" in aov_list
        vl.use_pass_transmission_indirect = "transmission_indirect" in aov_list
        vl.use_pass_transmission_color = "transmission_color" in aov_list
        cycles.use_pass_volume_direct = "volume_light" in aov_list
        cycles.use_pass_volume_indirect = "volume_indirect" in aov_list
        cycles.use_pass_shadow_catcher = "shadow" in aov_list

    aovs_names = [aov.name for aov in vl.aovs]
    for cp in custom_passes:
        cp_name = cp["attribute"] if AYON_SERVER_ENABLED else cp[0]
        if cp_name not in aovs_names:
            aov = vl.aovs.add()
            aov.name = cp_name
        else:
            aov = vl.aovs[cp_name]
        aov.type = (cp["value"]
                    if AYON_SERVER_ENABLED else cp[1].get("type", "VALUE"))

    return list(aov_list), custom_passes


def _create_aov_slot(name, aov_sep, slots, rpass_name, multi_exr, output_path):
    filename = f"{name}{aov_sep}{rpass_name}.####"
    slot = slots.new(rpass_name if multi_exr else filename)
    filepath = str(output_path / filename.lstrip("/"))

    return slot, filepath


def set_node_tree(
    output_path, render_product, name, aov_sep, ext, multilayer, compositing
):
    # Set the scene to use the compositor node tree to render
    bpy.context.scene.use_nodes = True

    tree = bpy.context.scene.node_tree

    comp_layer_type = "CompositorNodeRLayers"
    output_type = "CompositorNodeOutputFile"
    compositor_type = "CompositorNodeComposite"

    # Get the Render Layer, Composite and the previous output nodes
    render_layer_node = None
    composite_node = None
    old_output_node = None
    for node in tree.nodes:
        if node.bl_idname == comp_layer_type:
            render_layer_node = node
        elif node.bl_idname == compositor_type:
            composite_node = node
        elif node.bl_idname == output_type and "AYON" in node.name:
            old_output_node = node
        if render_layer_node and composite_node and old_output_node:
            break

    # If there's not a Render Layers node, we create it
    if not render_layer_node:
        render_layer_node = tree.nodes.new(comp_layer_type)

    # Get the enabled output sockets, that are the active passes for the
    # render.
    # We also exclude some layers.
    exclude_sockets = ["Image", "Alpha", "Noisy Image"]
    passes = [
        socket
        for socket in render_layer_node.outputs
        if socket.enabled and socket.name not in exclude_sockets
    ]

    # Create a new output node
    output = tree.nodes.new(output_type)

    image_settings = bpy.context.scene.render.image_settings
    output.format.file_format = image_settings.file_format

    slots = None

    # In case of a multilayer exr, we don't need to use the output node,
    # because the blender render already outputs a multilayer exr.
    multi_exr = ext == "exr" and multilayer
    slots = output.layer_slots if multi_exr else output.file_slots
    output.base_path = render_product if multi_exr else str(output_path)

    slots.clear()

    aov_file_products = []

    old_links = {
        link.from_socket.name: link for link in tree.links
        if link.to_node == old_output_node}

    # Create a new socket for the beauty output
    pass_name = "rgba" if multi_exr else "beauty"
    slot, _ = _create_aov_slot(
        name, aov_sep, slots, pass_name, multi_exr, output_path)
    tree.links.new(render_layer_node.outputs["Image"], slot)

    if compositing:
        # Create a new socket for the composite output
        pass_name = "composite"
        comp_socket, filepath = _create_aov_slot(
            name, aov_sep, slots, pass_name, multi_exr, output_path)
        aov_file_products.append(("Composite", filepath))

    # For each active render pass, we add a new socket to the output node
    # and link it
    for rpass in passes:
        slot, filepath = _create_aov_slot(
            name, aov_sep, slots, rpass.name, multi_exr, output_path)
        aov_file_products.append((rpass.name, filepath))

        # If the rpass was not connected with the old output node, we connect
        # it with the new one.
        if not old_links.get(rpass.name):
            tree.links.new(rpass, slot)

    for link in list(old_links.values()):
        # Check if the socket is still available in the new output node.
        socket = output.inputs.get(link.to_socket.name)
        # If it is, we connect it with the new output node.
        if socket:
            tree.links.new(link.from_socket, socket)
        # Then, we remove the old link.
        tree.links.remove(link)

    # If there's a composite node, we connect its input with the new output
    if compositing and composite_node:
        for link in tree.links:
            if link.to_node == composite_node:
                tree.links.new(link.from_socket, comp_socket)
                break

    if old_output_node:
        output.location = old_output_node.location
        tree.nodes.remove(old_output_node)

    output.name = "AYON File Output"
    output.label = "AYON File Output"

    return [] if multi_exr else aov_file_products


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

    filepath = Path(bpy.data.filepath)
    assert filepath, "Workfile not saved. Please save the file first."

    dirpath = filepath.parent
    file_name = Path(filepath.name).stem

    project = get_current_project_name()
    settings = get_project_settings(project)

    render_folder = get_default_render_folder(settings)
    aov_sep = get_aov_separator(settings)
    ext = get_image_format(settings)
    multilayer = get_multilayer(settings)
    renderer = get_renderer(settings)
    compositing = get_compositing(settings)

    set_render_format(ext, multilayer)
    bpy.context.scene.render.engine = renderer
    aov_list, custom_passes = set_render_passes(settings, renderer)

    output_path = Path.joinpath(dirpath, render_folder, file_name)

    render_product = get_render_product(output_path, name, aov_sep)
    aov_file_product = set_node_tree(
        output_path, render_product, name, aov_sep,
        ext, multilayer, compositing)

    # Clear the render filepath, so that the output is handled only by the
    # output node in the compositor.
    bpy.context.scene.render.filepath = ""

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
