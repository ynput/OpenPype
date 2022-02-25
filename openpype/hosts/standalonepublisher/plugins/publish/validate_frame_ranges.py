import re

import pyblish.api
import openpype.api
from openpype import lib


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Validating frame range of rendered files against state in DB."""

    label = "Validate Frame Range"
    hosts = ["standalonepublisher"]
    families = ["render"]
    order = openpype.api.ValidateContentsOrder

    optional = True
    # published data might be sequence (.mov, .mp4) in that counting files
    # doesnt make sense
    check_extensions = ["exr", "dpx", "jpg", "jpeg", "png", "tiff", "tga",
                        "gif", "svg"]
    skip_timelines_check = []  # skip for specific task names (regex)

    def process(self, instance):
        if any(re.search(pattern, instance.data["task"])
               for pattern in self.skip_timelines_check):
            self.log.info("Skipping for {} task".format(instance.data["task"]))

        asset_doc = instance.data.get("assetEntity")
        if not asset_doc:
            asset_doc = lib.get_asset(instance.data["asset"])
        frame_info = lib.get_frame_info(asset_doc)
        duration = frame_info.frame_range

        repre = instance.data.get("representations", [None])
        if not repre:
            self.log.info("No representations, skipping.")
            return

        ext = repre[0]['ext'].replace(".", '')

        if not ext or ext.lower() not in self.check_extensions:
            self.log.warning("Cannot check for extension {}".format(ext))
            return

        files = instance.data.get("representations", [None])[0]["files"]
        if isinstance(files, str):
            files = [files]
        frames = len(files)

        err_msg = "Frame duration from DB:'{}' ". format(int(duration)) +\
                  " doesn't match number of files:'{}'".format(frames) +\
                  " Please change frame range for Asset or limit no. of files"
        assert frames == duration, err_msg

        self.log.debug("Valid ranges {} - {}".format(int(duration), frames))
