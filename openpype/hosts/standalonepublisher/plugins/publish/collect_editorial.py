"""
Optional:
    presets     -> extensions (
        example of use:
            ["mov", "mp4"]
    )
    presets     -> source_dir (
        example of use:
            "C:/pathToFolder"
            "{root}/{project[name]}/inputs"
            "{root[work]}/{project[name]}/inputs"
            "./input"
            "../input"
            ""
    )
"""

import os
import opentimelineio as otio
import pyblish.api
from openpype import lib as plib
from openpype.pipeline.context_tools import get_current_project_asset


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
        plib.run_subprocess(["otioview", file_path])


class CollectEditorial(pyblish.api.InstancePlugin):
    """Collect Editorial OTIO timeline"""

    order = pyblish.api.CollectorOrder
    label = "Collect Editorial"
    hosts = ["standalonepublisher"]
    families = ["editorial"]
    actions = []

    # presets
    extensions = ["mov", "mp4"]
    source_dir = None

    def process(self, instance):
        root_dir = None
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

            if self.source_dir != "":
                source_dir = self.source_dir.replace("\\", "/")
                if ("./" in source_dir) or ("../" in source_dir):
                    # get current working dir
                    cwd = os.getcwd()
                    # set cwd to staging dir for absolute path solving
                    os.chdir(staging_dir)
                    root_dir = os.path.abspath(source_dir)
                    # set back original cwd
                    os.chdir(cwd)
                elif "{" in source_dir:
                    root_dir = source_dir
                else:
                    root_dir = os.path.normpath(source_dir)

            if root_dir:
                # search for source data will need to be done
                instance.data["editorialSourceRoot"] = root_dir
                instance.data["editorialSourcePath"] = None
            else:
                # source data are already found
                for f in os.listdir(staging_dir):
                    # filter out by not sharing the same name
                    if os.path.splitext(f)[0] not in basename:
                        continue
                    # filter out by respected extensions
                    if os.path.splitext(f)[1][1:] not in self.extensions:
                        continue
                    video_path = os.path.join(
                        staging_dir, f
                    )
                    self.log.debug(f"__ video_path: `{video_path}`")
                instance.data["editorialSourceRoot"] = staging_dir
                instance.data["editorialSourcePath"] = video_path

            instance.data["stagingDir"] = staging_dir

            # get editorial sequence file into otio timeline object
            extension = os.path.splitext(file_path)[1]
            kwargs = {}
            if extension == ".edl":
                # EDL has no frame rate embedded so needs explicit
                # frame rate else 24 is assumed.
                kwargs["rate"] = get_current_project_asset()["data"]["fps"]

            instance.data["otio_timeline"] = otio.adapters.read_from_file(
                file_path, **kwargs)

            self.log.info(f"Added OTIO timeline from: `{file_path}`")
