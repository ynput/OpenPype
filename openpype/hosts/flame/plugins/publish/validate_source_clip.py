import pyblish


@pyblish.api.log
class ValidateSourceClip(pyblish.api.InstancePlugin):
    """Validate instance is not having empty `flameSourceClip`"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Source Clip"
    hosts = ["flame"]
    families = ["clip"]

    def process(self, instance):
        flame_source_clip = instance.data["flameSourceClip"]

        self.log.debug("_ flame_source_clip: {}".format(flame_source_clip))

        if flame_source_clip is None:
            raise AttributeError((
                "Timeline segment `{}` is not having "
                "relative clip in reels. Please make sure "
                "you push `Save Sources` button in Conform Tab").format(
                    instance.data["asset"]
            ))
