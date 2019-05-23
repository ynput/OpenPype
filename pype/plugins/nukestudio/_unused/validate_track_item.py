from pyblish import api

class ValidateClip(api.InstancePlugin):
    """Validate the track item to the sequence.

    Exact matching to optimize processing.
    """

    order = api.ValidatorOrder
    families = ["clip"]
    # match = api.Exact
    label = "Validate Track Item"
    hosts = ["nukestudio"]
    optional = True

    def process(self, instance):

        item = instance.data["item"]
        self.log.info("__ item: {}".format(item))
        media_source = item.source().mediaSource()
        self.log.info("__ media_source: {}".format(media_source))

        msg = (
            'A setting does not match between track item "{0}" and sequence '
            '"{1}".'.format(item.name(), item.sequence().name()) +
            '\n\nSetting: "{0}".''\n\nTrack item: "{1}".\n\nSequence: "{2}".'
        )

        # Validate format settings.
        fmt = item.sequence().format()
        assert fmt.width() == media_source.width(), msg.format(
            "width", fmt.width(), media_source.width()
        )
        assert fmt.height() == media_source.height(), msg.format(
            "height", fmt.height(), media_source.height()
        )
        assert fmt.pixelAspect() == media_source.pixelAspect(), msg.format(
            "pixelAspect", fmt.pixelAspect(), media_source.pixelAspect()
        )

        # Validate framerate setting.
        sequence = item.sequence()
        source_framerate = media_source.metadata()["foundry.source.framerate"]
        assert sequence.framerate() == source_framerate, msg.format(
            "framerate", source_framerate, sequence.framerate()
        )
