import substance_painter.export

from openpype.pipeline import KnownPublishError, publish


class ExtractTextures(publish.Extractor,
                      publish.ColormanagedPyblishPluginMixin):
    """Extract Textures using an output template config.

    Note:
        This Extractor assumes that `collect_textureset_images` has prepared
        the relevant export config and has also collected the individual image
        instances for publishing including its representation. That is why this
        particular Extractor doesn't specify representations to integrate.

    """

    label = "Extract Texture Set"
    hosts = ["substancepainter"]
    families = ["textureSet"]

    # Run before thumbnail extractors
    order = publish.Extractor.order - 0.1

    def process(self, instance):

        config = instance.data["exportConfig"]
        result = substance_painter.export.export_project_textures(config)

        if result.status != substance_painter.export.ExportStatus.Success:
            raise KnownPublishError(
                "Failed to export texture set: {}".format(result.message)
            )

        # Log what files we generated
        for (texture_set_name, stack_name), maps in result.textures.items():
            # Log our texture outputs
            self.log.info(f"Exported stack: {texture_set_name} {stack_name}")
            for texture_map in maps:
                self.log.info(f"Exported texture: {texture_map}")

        # We'll insert the color space data for each image instance that we
        # added into this texture set. The collector couldn't do so because
        # some anatomy and other instance data needs to be collected prior
        context = instance.context
        for image_instance in instance:
            representation = next(iter(image_instance.data["representations"]))

            colorspace = image_instance.data.get("colorspace")
            if not colorspace:
                self.log.debug("No color space data present for instance: "
                               f"{image_instance}")
                continue

            self.set_representation_colorspace(representation,
                                               context=context,
                                               colorspace=colorspace)

        # The TextureSet instance should not be integrated. It generates no
        # output data. Instead the separated texture instances are generated
        # from it which themselves integrate into the database.
        instance.data["integrate"] = False
