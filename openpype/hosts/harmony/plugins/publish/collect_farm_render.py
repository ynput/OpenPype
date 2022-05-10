# -*- coding: utf-8 -*-
"""Collect data to render from scene."""
from pathlib import Path

import attr

import openpype.lib
import openpype.lib.abstract_collect_render
from openpype.lib.abstract_collect_render import RenderInstance
from openpype.lib import get_formatted_current_time
from openpype.pipeline import legacy_io
import openpype.hosts.harmony.api as harmony


@attr.s
class HarmonyRenderInstance(RenderInstance):
    outputType = attr.ib(default="Image")
    outputFormat = attr.ib(default="PNG4")
    outputStartFrame = attr.ib(default=1)
    leadingZeros = attr.ib(default=3)


class CollectFarmRender(openpype.lib.abstract_collect_render.
                        AbstractCollectRender):
    """Gather all publishable renders."""

    # https://docs.toonboom.com/help/harmony-17/premium/reference/node/output/write-node-image-formats.html
    ext_mapping = {
        "tvg": ["TVG"],
        "tga": ["TGA", "TGA4", "TGA3", "TGA1"],
        "sgi": ["SGI", "SGI4", "SGA3", "SGA1", "SGIDP", "SGIDP4", "SGIDP3"],
        "psd": ["PSD", "PSD1", "PSD3", "PSD4", "PSDDP", "PSDDP1", "PSDDP3",
                "PSDDP4"],
        "yuv": ["YUV"],
        "pal": ["PAL"],
        "scan": ["SCAN"],
        "png": ["PNG", "PNG4", "PNGDP", "PNGDP3", "PNGDP4"],
        "jpg": ["JPG"],
        "bmp": ["BMP", "BMP4"],
        "opt": ["OPT", "OPT1", "OPT3", "OPT4"],
        "var": ["VAR"],
        "tif": ["TIF"],
        "dpx": ["DPX", "DPX3_8", "DPX3_10", "DPX3_12", "DPX3_16",
                "DPX3_10_INVERTED_CHANNELS", "DPX3_12_INVERTED_CHANNELS",
                "DPX3_16_INVERTED_CHANNELS"],
        "exr": ["EXR"],
        "pdf": ["PDF"],
        "dtext": ["DTEX"]
    }

    def get_expected_files(self, render_instance):
        """Get list of expected files to be rendered from Harmony.

        This returns full path with file name determined by Write node
        settings.
        """
        start = render_instance.frameStart - render_instance.handleStart
        end = render_instance.frameEnd + render_instance.handleEnd
        node = render_instance.setMembers[0]
        self_name = self.__class__.__name__
        # 0 - filename / 1 - type / 2 - zeros / 3 - start
        info = harmony.send(
            {
                "function": f"PypeHarmony.Publish.{self_name}."
                            "getRenderNodeSettings",
                "args": node
            })["result"]

        ext = None
        for k, v in self.ext_mapping.items():
            if info[1] in v:
                ext = k

        if not ext:
            raise AssertionError(
                f"Cannot determine file extension for {info[1]}")

        path = Path(render_instance.source).parent
        # is sequence start node on write node offsetting whole sequence?
        expected_files = []

        # '-' in name is important for Harmony17
        for frame in range(start, end + 1):
            expected_files.append(
                path / "{}-{}.{}".format(
                    render_instance.subset,
                    str(frame).rjust(int(info[2]) + 1, "0"),
                    ext
                )
            )
        self.log.debug("expected_files::{}".format(expected_files))
        return expected_files

    def get_instances(self, context):
        """Get instances per Write node in `renderFarm` family."""
        version = None
        if self.sync_workfile_version:
            version = context.data["version"]

        instances = []

        self_name = self.__class__.__name__

        for node in context.data["allNodes"]:
            data = harmony.read(node)

            # Skip non-tagged nodes.
            if not data:
                continue

            # Skip containers.
            if "container" in data["id"]:
                continue

            if data["family"] != "renderFarm":
                continue

            # 0 - filename / 1 - type / 2 - zeros / 3 - start / 4 - enabled
            info = harmony.send(
                {
                    "function": f"PypeHarmony.Publish.{self_name}."
                                "getRenderNodeSettings",
                    "args": node
                })["result"]

            # TODO: handle pixel aspect and frame step
            # TODO: set Deadline stuff (pools, priority, etc. by presets)
            # because of using 'renderFarm' as a family, replace 'Farm' with
            # capitalized task name - issue of avalon-core Creator app
            subset_name = node.split("/")[1]
            task_name = context.data["anatomyData"]["task"][
                "name"].capitalize()
            replace_str = ""
            if task_name.lower() not in subset_name.lower():
                replace_str = task_name
            subset_name = subset_name.replace(
                'Farm',
                replace_str)

            render_instance = HarmonyRenderInstance(
                version=version,
                time=get_formatted_current_time(),
                source=context.data["currentFile"],
                label=node.split("/")[1],
                subset=subset_name,
                asset=legacy_io.Session["AVALON_ASSET"],
                attachTo=False,
                setMembers=[node],
                publish=info[4],
                review=False,
                renderer=None,
                priority=50,
                name=node.split("/")[1],

                family="render.farm",
                families=["render.farm"],

                resolutionWidth=context.data["resolutionWidth"],
                resolutionHeight=context.data["resolutionHeight"],
                pixelAspect=1.0,
                multipartExr=False,
                tileRendering=False,
                tilesX=0,
                tilesY=0,
                convertToScanline=False,

                # time settings
                frameStart=context.data["frameStart"],
                frameEnd=context.data["frameEnd"],
                handleStart=context.data["handleStart"],  # from DB
                handleEnd=context.data["handleEnd"],      # from DB
                frameStep=1,
                outputType="Image",
                outputFormat=info[1],
                outputStartFrame=info[3],
                leadingZeros=info[2],
                toBeRenderedOn='deadline',
                ignoreFrameHandleCheck=True

            )
            render_instance.context = context
            self.log.debug(render_instance)
            instances.append(render_instance)

        return instances

    def add_additional_data(self, instance):
        instance["FOV"] = self._context.data["FOV"]

        return instance
