import os
import copy
import clique
import pyblish.api

from openpype.pipeline import publish

import substance_painter.export
from openpype.hosts.substancepainter.api.colorspace import (
    get_project_channel_data,
)


def get_project_color_spaces():
    """Return unique color space names used for exports.

    This is based on the Color Management preferences of the project.

    See also:
        func:`get_project_channel_data`

    """
    return set(
        data["colorSpace"] for data in get_project_channel_data().values()
    )


def _get_channel_name(path,
                      texture_set_name,
                      project_colorspaces):
    """Return expected 'name' for the output image.

    This will be used as a suffix to the separate image publish subsets.

    """
    # TODO: This will require improvement before being production ready.
    # TODO(Question): Should we preserve the texture set name in the suffix
    # TODO so that exports with multiple texture sets can work within a single
    # TODO parent textureSet, like `texture{Variant}.{TextureSet}{Channel}`
    name = os.path.basename(path)  # filename
    name = os.path.splitext(name)[0]  # no extension
    # Usually the channel identifier comes after $textureSet in
    # the export preset. Unfortunately getting the export maps
    # and channels explicitly is not trivial so for now we just
    # assume this will generate a nice identifier for the end user
    name = name.split(f"{texture_set_name}_", 1)[-1]

    # TODO: We need more explicit ways to detect the color space part
    for colorspace in project_colorspaces:
        if name.endswith(f"_{colorspace}"):
            name = name[:-len(f"_{colorspace}")]
            break

    return name


class CollectTextureSet(pyblish.api.InstancePlugin):
    """Extract Textures using an output template config"""
    # TODO: More explicitly detect UDIM tiles
    # TODO: Get color spaces
    # TODO: Detect what source data channels end up in each file

    label = "Collect Texture Set images"
    hosts = ['substancepainter']
    families = ["textureSet"]
    order = pyblish.api.CollectorOrder

    def process(self, instance):

        config = self.get_export_config(instance)
        textures = substance_painter.export.list_project_textures(config)

        instance.data["exportConfig"] = config

        colorspaces = get_project_color_spaces()

        outputs = {}
        for (texture_set_name, stack_name), maps in textures.items():

            # Log our texture outputs
            self.log.debug(f"Processing stack: {stack_name}")
            for texture_map in maps:
                self.log.debug(f"Expecting texture: {texture_map}")

            # For now assume the UDIM textures end with .<UDIM>.<EXT> and
            # when no trailing number is present before the extension then it's
            # considered to *not* be a UDIM export.
            collections, remainder = clique.assemble(
                maps,
                patterns=[clique.PATTERNS["frames"]],
                minimum_items=True
            )

            outputs = {}
            if collections:
                # UDIM tile sequence
                for collection in collections:
                    name = _get_channel_name(collection.head,
                                             texture_set_name=texture_set_name,
                                             project_colorspaces=colorspaces)
                    outputs[name] = collection
                    self.log.info(f"UDIM Collection: {collection}")
            else:
                # Single file per channel without UDIM number
                for path in remainder:
                    name = _get_channel_name(path,
                                             texture_set_name=texture_set_name,
                                             project_colorspaces=colorspaces)
                    outputs[name] = path
                    self.log.info(f"Single file: {path}")

        # Let's break the instance into multiple instances to integrate
        # a subset per generated texture or texture UDIM sequence
        context = instance.context
        for map_name, map_output in outputs.items():

            is_udim = isinstance(map_output, clique.Collection)
            if is_udim:
                first_file = list(map_output)[0]
                map_fnames = [os.path.basename(path) for path in map_output]
            else:
                first_file = map_output
                map_fnames = os.path.basename(map_output)

            ext = os.path.splitext(first_file)[1]
            assert ext.lstrip('.'), f"No extension: {ext}"

            # Define the suffix we want to give this particular texture
            # set and set up a remapped subset naming for it.
            suffix = f".{map_name}"
            image_subset = instance.data["subset"][len("textureSet"):]
            image_subset = "texture" + image_subset + suffix

            # TODO: Retrieve and store color space with the representation

            # Clone the instance
            image_instance = context.create_instance(instance.name)
            image_instance[:] = instance[:]
            image_instance.data.update(copy.deepcopy(instance.data))
            image_instance.data["name"] = image_subset
            image_instance.data["label"] = image_subset
            image_instance.data["subset"] = image_subset
            image_instance.data["family"] = "image"
            image_instance.data["families"] = ["image", "textures"]
            image_instance.data['representations'] = [{
                'name': ext.lstrip("."),
                'ext': ext.lstrip("."),
                'files': map_fnames,
            }]

            # Group the textures together in the loader
            image_instance.data["subsetGroup"] = instance.data["subset"]

            # Set up the representation for thumbnail generation
            # TODO: Simplify this once thumbnail extraction is refactored
            staging_dir = os.path.dirname(first_file)
            image_instance.data["representations"][0]["tags"] = ["review"]
            image_instance.data["representations"][0]["stagingDir"] = staging_dir  # noqa

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
