import nuke
import pyblish.api


class CollectInstanceData(pyblish.api.InstancePlugin):
    """Collect all nodes with Avalon knob."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Collect Instance Data"
    hosts = ["nuke", "nukeassist"]

    # presets
    sync_workfile_version_on_families = []

    def process(self, instance):
        family = instance.data["family"]

        # Get format
        root = nuke.root()
        format_ = root['format'].value()
        resolution_width = format_.width()
        resolution_height = format_.height()
        pixel_aspect = format_.pixelAspect()

        # sync workfile version
        if family in self.sync_workfile_version_on_families:
            self.log.debug(
                "Syncing version with workfile for '{}'".format(
                    family
                )
            )
            # get version to instance for integration
            instance.data['version'] = instance.context.data['version']

        instance.data.update({
            "step": 1,
            "fps": root['fps'].value(),
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect

        })
        self.log.debug("Collected instance: {}".format(
            instance.data))
