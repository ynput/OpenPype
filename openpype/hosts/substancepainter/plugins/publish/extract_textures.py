from openpype.pipeline import KnownPublishError, publish

import substance_painter.export


class ExtractTextures(publish.Extractor):
    """Extract Textures using an output template config"""

    label = "Extract Texture Sets"
    hosts = ['substancepainter']
    families = ["textures"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)

        # See: https://substance3d.adobe.com/documentation/ptpy/api/substance_painter/export  # noqa
        creator_attrs = instance.data["creator_attributes"]
        config = {
            "exportShaderParams": True,
            "exportPath": staging_dir,
            "defaultExportPreset": creator_attrs["exportPresetUrl"],

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
            # stack = texture_set.get_stack()
            config["exportList"].append({"rootPath": texture_set.name()})

        # Consider None values optionals
        for override in config["exportParameters"]:
            parameters = override.get("parameters")
            for key, value in dict(parameters).items():
                if value is None:
                    parameters.pop(key)

        result = substance_painter.export.export_project_textures(config)

        if result.status != substance_painter.export.ExportStatus.Success:
            raise KnownPublishError(
                "Failed to export texture set: {}".format(result.message)
            )

        files = []
        for _stack, maps in result.textures.items():
            for texture_map in maps:
                self.log.info(f"Exported texture: {texture_map}")
                files.append(texture_map)

        # TODO: add the representations so they integrate the way we'd want
        """
        instance.data['representations'] = [{
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': file,
            "stagingDir": folder,
        }]
        """
