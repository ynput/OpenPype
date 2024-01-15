import os
import copy
import pyblish.api

from openpype.pipeline import publish

import substance_painter.textureset
from openpype.hosts.substancepainter.api.lib import (
    get_parsed_export_maps,
    strip_template
)
from openpype.pipeline.create import get_subset_name
from openpype.client import get_asset_by_name


class CollectTextureSet(pyblish.api.InstancePlugin):
    """Extract Textures using an output template config"""
    # TODO: Production-test usage of color spaces
    # TODO: Detect what source data channels end up in each file

    label = "Collect Texture Set images"
    hosts = ["substancepainter"]
    families = ["textureSet"]
    order = pyblish.api.CollectorOrder

    def process(self, instance):

        config = self.get_export_config(instance)
        asset_doc = get_asset_by_name(
            project_name=instance.context.data["projectName"],
            asset_name=instance.data["asset"]
        )

        instance.data["exportConfig"] = config
        maps = get_parsed_export_maps(config)

        # Let's break the instance into multiple instances to integrate
        # a subset per generated texture or texture UDIM sequence
        for (texture_set_name, stack_name), template_maps in maps.items():
            self.log.info(f"Processing {texture_set_name}/{stack_name}")
            for template, outputs in template_maps.items():
                self.log.info(f"Processing {template}")
                self.create_image_instance(instance, template, outputs,
                                           asset_doc=asset_doc,
                                           texture_set_name=texture_set_name,
                                           stack_name=stack_name)

    def create_image_instance(self, instance, template, outputs,
                              asset_doc, texture_set_name, stack_name):
        """Create a new instance per image or UDIM sequence.

        The new instances will be of family `image`.

        """

        context = instance.context
        first_filepath = outputs[0]["filepath"]
        fnames = [os.path.basename(output["filepath"]) for output in outputs]
        ext = os.path.splitext(first_filepath)[1]
        assert ext.lstrip("."), f"No extension: {ext}"

        always_include_texture_set_name = False  # todo: make this configurable
        all_texture_sets = substance_painter.textureset.all_texture_sets()
        texture_set = substance_painter.textureset.TextureSet.from_name(
            texture_set_name
        )

        # Define the suffix we want to give this particular texture
        # set and set up a remapped subset naming for it.
        suffix = ""
        if always_include_texture_set_name or len(all_texture_sets) > 1:
            # More than one texture set, include texture set name
            suffix += f".{texture_set_name}"
        if texture_set.is_layered_material() and stack_name:
            # More than one stack, include stack name
            suffix += f".{stack_name}"

        # Always include the map identifier
        map_identifier = strip_template(template)
        suffix += f".{map_identifier}"

        image_subset = get_subset_name(
            # TODO: The family actually isn't 'texture' currently but for now
            #       this is only done so the subset name starts with 'texture'
            family="texture",
            variant=instance.data["variant"] + suffix,
            task_name=instance.data.get("task"),
            asset_doc=asset_doc,
            project_name=context.data["projectName"],
            host_name=context.data["hostName"],
            project_settings=context.data["project_settings"]
        )

        # Prepare representation
        representation = {
            "name": ext.lstrip("."),
            "ext": ext.lstrip("."),
            "files": fnames if len(fnames) > 1 else fnames[0],
        }

        # Mark as UDIM explicitly if it has UDIM tiles.
        if bool(outputs[0].get("udim")):
            # The representation for a UDIM sequence should have a `udim` key
            # that is a list of all udim tiles (str) like: ["1001", "1002"]
            # strings. See CollectTextures plug-in and Integrators.
            representation["udim"] = [output["udim"] for output in outputs]

        # Set up the representation for thumbnail generation
        # TODO: Simplify this once thumbnail extraction is refactored
        staging_dir = os.path.dirname(first_filepath)
        representation["tags"] = ["review"]
        representation["stagingDir"] = staging_dir

        # Clone the instance
        image_instance = context.create_instance(image_subset)
        image_instance[:] = instance[:]
        image_instance.data.update(copy.deepcopy(dict(instance.data)))
        image_instance.data["name"] = image_subset
        image_instance.data["label"] = image_subset
        image_instance.data["subset"] = image_subset
        image_instance.data["family"] = "image"
        image_instance.data["families"] = ["image", "textures"]
        image_instance.data["representations"] = [representation]

        # Group the textures together in the loader
        image_instance.data["subsetGroup"] = instance.data["subset"]

        # Store the texture set name and stack name on the instance
        image_instance.data["textureSetName"] = texture_set_name
        image_instance.data["textureStackName"] = stack_name

        # Store color space with the instance
        # Note: The extractor will assign it to the representation
        colorspace = outputs[0].get("colorSpace")
        if colorspace:
            self.log.debug(f"{image_subset} colorspace: {colorspace}")
            image_instance.data["colorspace"] = colorspace

        # Store the instance in the original instance as a member
        instance.append(image_instance)

    def get_export_config(self, instance):
        """Return an export configuration dict for texture exports.

        This config can be supplied to:
            - `substance_painter.export.export_project_textures`
            - `substance_painter.export.list_project_textures`

        See documentation on substance_painter.export module about the
        formatting of the configuration dictionary.

        Args:
            instance (pyblish.api.Instance): Texture Set instance to be
                published.

        Returns:
            dict: Export config

        """

        creator_attrs = instance.data["creator_attributes"]
        preset_url = creator_attrs["exportPresetUrl"]
        self.log.debug(f"Exporting using preset: {preset_url}")

        # See: https://substance3d.adobe.com/documentation/ptpy/api/substance_painter/export  # noqa
        config = {  # noqa
            "exportShaderParams": True,
            "exportPath": publish.get_instance_staging_dir(instance),
            "defaultExportPreset": preset_url,

            # Custom overrides to the exporter
            "exportParameters": [
                {
                    "parameters": {
                        "fileFormat": creator_attrs["exportFileFormat"],
                        "sizeLog2": creator_attrs["exportSize"],
                        "paddingAlgorithm": creator_attrs["exportPadding"],
                        "dilationDistance": creator_attrs["exportDilationDistance"]  # noqa
                    }
                }
            ]
        }

        # Create the list of Texture Sets to export.
        config["exportList"] = []
        for texture_set in substance_painter.textureset.all_texture_sets():
            config["exportList"].append({"rootPath": texture_set.name()})

        # Consider None values from the creator attributes optionals
        for override in config["exportParameters"]:
            parameters = override.get("parameters")
            for key, value in dict(parameters).items():
                if value is None:
                    parameters.pop(key)

        return config
