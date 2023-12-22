import re

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin,
)


class ValidateFrameRange(OptionalPyblishPluginMixin,
                         pyblish.api.InstancePlugin):
    """Validating frame range of rendered files against state in DB."""

    label = "Validate Frame Range"
    hosts = ["traypublisher"]
    families = ["render", "plate"]
    order = ValidateContentsOrder

    optional = True
    # published data might be sequence (.mov, .mp4) in that counting files
    # doesnt make sense
    check_extensions = ["exr", "dpx", "jpg", "jpeg", "png", "tiff", "tga",
                        "gif", "svg"]
    skip_timelines_check = []  # skip for specific task names (regex)

    def process(self, instance):
        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return

        # editorial would fail since they might not be in database yet
        new_asset_publishing = instance.data.get("newAssetPublishing")
        if new_asset_publishing:
            self.log.debug("Instance is creating new asset. Skipping.")
            return

        if (self.skip_timelines_check and
            any(re.search(pattern, instance.data["task"])
                for pattern in self.skip_timelines_check)):
            self.log.info("Skipping for {} task".format(instance.data["task"]))

        asset_doc = instance.data["assetEntity"]
        asset_data = asset_doc["data"]
        frame_start = asset_data["frameStart"]
        frame_end = asset_data["frameEnd"]
        handle_start = asset_data["handleStart"]
        handle_end = asset_data["handleEnd"]
        duration = (frame_end - frame_start + 1) + handle_start + handle_end

        repres = instance.data.get("representations")
        if not repres:
            self.log.info("No representations, skipping.")
            return

        first_repre = repres[0]
        ext = first_repre['ext'].replace(".", '')

        if not ext or ext.lower() not in self.check_extensions:
            self.log.warning("Cannot check for extension {}".format(ext))
            return

        files = first_repre["files"]
        if isinstance(files, str):
            files = [files]
        frames = len(files)

        msg = (
            "Frame duration from DB:'{}' doesn't match number of files:'{}'"
            " Please change frame range for Asset or limit no. of files"
        ). format(int(duration), frames)

        formatting_data = {"duration": duration,
                           "found": frames}
        if frames != duration:
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)

        self.log.debug("Valid ranges expected '{}' - found '{}'".
                       format(int(duration), frames))
