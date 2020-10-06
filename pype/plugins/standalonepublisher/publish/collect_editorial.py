import os
import opentimelineio as otio
import pyblish.api
from pype import lib as plib


class OTIO_View(pyblish.api.Action):
    """Currently disabled because OTIO requires PySide2. Issue on Qt.py:
    https://github.com/PixarAnimationStudios/OpenTimelineIO/issues/289
    """

    label = "OTIO View"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        instance = context[0]
        representation = instance.data["representations"][0]
        file_path = os.path.join(
            representation["stagingDir"], representation["files"]
        )
        plib._subprocess(["otioview", file_path])


class CollectEditorial(pyblish.api.InstancePlugin):
    """Collect Editorial OTIO timeline"""

    order = pyblish.api.CollectorOrder
    label = "Collect Editorial"
    hosts = ["standalonepublisher"]
    families = ["editorial"]
    actions = []

    # presets
    extensions = [".mov", ".mp4"]

    def process(self, instance):
        # remove context test attribute
        if instance.context.data.get("subsetNamesCheck"):
            instance.context.data.pop("subsetNamesCheck")

        self.log.debug(f"__ instance: `{instance}`")
        # get representation with editorial file
        for representation in instance.data["representations"]:
            self.log.debug(f"__ representation: `{representation}`")
            # make editorial sequence file path
            staging_dir = representation["stagingDir"]
            file_path = os.path.join(
                staging_dir, str(representation["files"])
            )
            instance.context.data["currentFile"] = file_path

            # get video file path
            video_path = None
            basename = os.path.splitext(os.path.basename(file_path))[0]
            for f in os.listdir(staging_dir):
                self.log.debug(f"__ test file: `{f}`")
                # filter out by not sharing the same name
                if os.path.splitext(f)[0] not in basename:
                    continue
                # filter out by respected extensions
                if os.path.splitext(f)[1] not in self.extensions:
                    continue
                video_path = os.path.join(
                    staging_dir, f
                )
                self.log.debug(f"__ video_path: `{video_path}`")
            instance.data["editorialVideoPath"] = video_path
            instance.data["stagingDir"] = staging_dir

            # get editorial sequence file into otio timeline object
            extension = os.path.splitext(file_path)[1]
            kwargs = {}
            if extension == ".edl":
                # EDL has no frame rate embedded so needs explicit
                # frame rate else 24 is asssumed.
                kwargs["rate"] = plib.get_asset()["data"]["fps"]

            instance.data["otio_timeline"] = otio.adapters.read_from_file(
                file_path, **kwargs)

            self.log.info(f"Added OTIO timeline from: `{file_path}`")
