"""Create render."""
import os

import bpy

from openpype.settings import get_project_settings
from openpype.pipeline import (
    get_current_project_name,
    get_current_task_name,
)
from openpype.hosts.blender.api import plugin, lib
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateRenderlayer(plugin.Creator):
    """Single baked camera"""

    name = "renderingMain"
    label = "Render"
    family = "renderlayer"
    icon = "eye"

    @staticmethod
    def get_default_render_folder(settings):
        """Get default render folder from blender settings."""

        return (settings["blender"]
                        ["RenderSettings"]
                        ["default_render_image_folder"])

    @staticmethod
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

    @staticmethod
    def get_image_format(settings):
        """Get image format from blender settings."""

        return (settings["blender"]
                        ["RenderSettings"]
                        ["image_format"])

    @staticmethod
    def get_multilayer(settings):
        """Get multilayer from blender settings."""

        return (settings["blender"]
                        ["RenderSettings"]
                        ["multilayer_exr"])

    @staticmethod
    def get_render_product(output_path, name):
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
        render_product = f"{os.path.join(output_path, name)}.####"
        render_product = render_product.replace("\\", "/")

        return render_product

    @staticmethod
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

    @staticmethod
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

    def set_node_tree(self, output_path, name, aov_sep, ext, multilayer):
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
        exclude_sockets = ["Image", "Alpha"]
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

        aov_file_products = []

        if ext == "exr" and multilayer:
            output.layer_slots.clear()
            filepath = f"{name}{aov_sep}AOVs.####"
            output.base_path = os.path.join(output_path, filepath)

            aov_file_products.append(
                ("AOVs", os.path.join(output_path, filepath)))
        else:
            output.file_slots.clear()
            output.base_path = output_path

        image_settings = bpy.context.scene.render.image_settings
        output.format.file_format = image_settings.file_format

        # For each active render pass, we add a new socket to the output node
        # and link it
        for render_pass in passes:
            if ext == "exr" and multilayer:
                output.layer_slots.new(render_pass.name)
            else:
                filepath = f"{name}{aov_sep}{render_pass.name}.####"

                output.file_slots.new(filepath)

                aov_file_products.append(
                    (render_pass.name, os.path.join(output_path, filepath)))

            node_input = output.inputs[-1]

            tree.links.new(render_pass, node_input)

        return aov_file_products

    @staticmethod
    def imprint_render_settings(node, data):
        RENDER_DATA = "render_data"
        if not node.get(RENDER_DATA):
            node[RENDER_DATA] = {}
        for key, value in data.items():
            if value is None:
                continue
            node[RENDER_DATA][key] = value

    def prepare_rendering(self, asset_group, name):
        filepath = bpy.data.filepath
        assert filepath, "Workfile not saved. Please save the file first."

        file_path = os.path.dirname(filepath)
        file_name = os.path.basename(filepath)
        file_name, _ = os.path.splitext(file_name)

        project = get_current_project_name()
        settings = get_project_settings(project)

        render_folder = self.get_default_render_folder(settings)
        aov_sep = self.get_aov_separator(settings)
        ext = self.get_image_format(settings)
        multilayer = self.get_multilayer(settings)

        aov_list, custom_passes = self.set_render_passes(settings)

        output_path = os.path.join(file_path, render_folder, file_name)

        render_product = self.get_render_product(output_path, name)
        aov_file_product = self.set_node_tree(
            output_path, name, aov_sep, ext, multilayer)

        # We set the render path, the format and the camera
        bpy.context.scene.render.filepath = render_product
        self.set_render_format(ext, multilayer)

        render_settings = {
            "render_folder": render_folder,
            "aov_separator": aov_sep,
            "image_format": ext,
            "multilayer_exr": multilayer,
            "aov_list": aov_list,
            "custom_passes": custom_passes,
            "render_product": render_product,
            "aov_file_product": aov_file_product,
        }

        self.imprint_render_settings(asset_group, render_settings)

    def process(self):
        # Get Instance Container or create it if it does not exist
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if not instances:
            instances = bpy.data.collections.new(name=AVALON_INSTANCES)
            bpy.context.scene.collection.children.link(instances)

        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)
        asset_group = bpy.data.collections.new(name=name)

        try:
            instances.children.link(asset_group)
            self.data['task'] = get_current_task_name()
            lib.imprint(asset_group, self.data)

            self.prepare_rendering(asset_group, name)
        except Exception:
            # Remove the instance if there was an error
            bpy.data.collections.remove(asset_group)
            raise

        # TODO: this is undesiderable, but it's the only way to be sure that
        # the file is saved before the render starts.
        # Blender, by design, doesn't set the file as dirty if modifications
        # happen by script. So, when creating the instance and setting the
        # render settings, the file is not marked as dirty. This means that
        # there is the risk of sending to deadline a file without the right
        # settings. Even the validator to check that the file is saved will
        # detect the file as saved, even if it isn't. The only solution for
        # now it is to force the file to be saved.
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

        return asset_group
