# -*- coding: utf-8 -*-
"""Collect render template.

TODO: use @dataclass when times come.

"""
from abc import ABCMeta, abstractmethod

import six
import attr

from avalon import api
import pyblish.api

from .abstract_expected_files import ExpectedFiles


@attr.s
class RenderInstance(object):
    """Data collected by collectors.

    This data class later on passed to collected instances.
    Those attributes are required later on.

    """

    # metadata
    version = attr.ib()
    time = attr.ib()
    source = attr.ib()
    label = attr.ib()
    subset = attr.ib()
    asset = attr.ib(init=False)
    attachTo = attr.ib(init=False)
    setMembers = attr.ib()
    publish = attr.ib()
    renderer = attr.ib()
    name = attr.ib()

    # format settings
    resolutionWidth = attr.ib()
    resolutionHeight = attr.ib()
    pixelAspect = attr.ib()

    tileRendering = attr.ib()
    tilesX = attr.ib()
    tilesY = attr.ib()

    # time settings
    frameStart = attr.ib()
    frameEnd = attr.ib()
    frameStep = attr.ib()

    # --------------------
    # With default values
    # metadata
    review = attr.ib(default=False)
    priority = attr.ib(default=50)

    family = attr.ib(default="renderlayer")
    families = attr.ib(default=["renderlayer"])

    # format settings
    multipartExr = attr.ib(default=False)
    convertToScanline = attr.ib(default=False)

    @frameStart.validator
    def check_frame_start(self, _, value):
        """Validate if frame start is not larger then end."""
        if value >= self.frameEnd:
            raise ValueError("frameStart must be smaller "
                             "or equal then frameEnd")

    @frameEnd.validator
    def check_frame_end(self, _, value):
        """Validate if frame end is not less then start."""
        if value <= self.frameStart:
            raise ValueError("frameEnd must be smaller "
                             "or equal then frameStart")

    @tilesX.validator
    def check_tiles_x(self, _, value):
        """Validate if tile x isn't less then 1."""
        if not self.tileRendering:
            return
        if value < 1:
            raise ValueError("tile X size cannot be less then 1")

        if value == 1 and self.tilesY == 1:
            raise ValueError("both tiles X a Y sizes are set to 1")

    @tilesY.validator
    def check_tiles_y(self, _, value):
        """Validate if tile y isn't less then 1."""
        if not self.tileRendering:
            return
        if value < 1:
            raise ValueError("tile Y size cannot be less then 1")

        if value == 1 and self.tilesX == 1:
            raise ValueError("both tiles X a Y sizes are set to 1")


@six.add_metaclass(ABCMeta)
class AbstractCollectRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Render"
    sync_workfile_version = False

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(AbstractCollectRender, self).__init__(*args, **kwargs)
        self._file_path = None
        self._asset = api.Session["AVALON_ASSET"]

    def process(self, context):
        """Entry point to collector."""
        for instance in context:
            # make sure workfile instance publishing is enabled
            if "workfile" in instance.data["families"]:
                instance.data["publish"] = True

        self._file_path = context.data["currentFile"].replace("\\", "/")

        render_instances = self.get_instances()
        for render_instance in render_instances:
            exp_files = self._get_expected_files(render_instance)

            frame_start_render = int(render_instance.frameStart)
            frame_end_render = int(render_instance.frameEnd)

            if (int(context.data['frameStartHandle']) == frame_start_render
                    and int(context.data['frameEndHandle']) == frame_end_render):  # noqa: W503, E501

                handle_start = context.data['handleStart']
                handle_end = context.data['handleEnd']
                frame_start = context.data['frameStart']
                frame_end = context.data['frameEnd']
                frame_start_handle = context.data['frameStartHandle']
                frame_end_handle = context.data['frameEndHandle']
            else:
                handle_start = 0
                handle_end = 0
                frame_start = frame_start_render
                frame_end = frame_end_render
                frame_start_handle = frame_start_render
                frame_end_handle = frame_end_render

            data = {
                "subset": render_instance.subset,
                "attachTo": render_instance.attachTo,
                "setMembers": render_instance.setMembers,
                "multipartExr": exp_files.multipart,
                "review": render_instance.review or False,
                "publish": True,

                "handleStart": handle_start,
                "handleEnd": handle_end,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartHandle": frame_start_handle,
                "frameEndHandle": frame_end_handle,
                "byFrameStep": int(render_instance.frameStep),
                "renderer": render_instance.renderer,
                # instance subset
                "family": render_instance.family,
                "families": render_instance.families,
                "asset": render_instance.asset,
                "time": render_instance.time,
                "author": context.data["user"],
                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": render_instance.source,
                "expectedFiles": exp_files,
                "resolutionWidth": render_instance.resolutionWidth,
                "resolutionHeight": render_instance.resolutionHeight,
                "pixelAspect": render_instance.pixelAspect,
                "tileRendering": render_instance.tileRendering or False,
                "tilesX": render_instance.tilesX or 2,
                "tilesY": render_instance.tilesY or 2,
                "priority": render_instance.priority,
                "convertToScanline": render_instance.convertToScanline or False
            }
            if self.sync_workfile_version:
                data["version"] = context.data["version"]

            # add additional data
            data = self.add_additional_data(data)

            instance = context.create_instance(render_instance.name)
            instance.data["label"] = render_instance.label
            instance.data.update(data)

        self.post_collecting_action()

    @abstractmethod
    def get_instances(self):
        """Get all renderable instances and their data.

        Returns:
            list of :class:`RenderInstance`: All collected renderable instances
                (like render layers, write nodes, etc.)

        """
        pass

    def _get_expected_files(self, render_instance):
        """Get list of expected files.

        Returns:
            list: expected files.

        """
        # return all expected files for all cameras and aovs in given
        # frame range
        ef = ExpectedFiles()
        exp_files = ef.get(render_instance)
        self.log.info("multipart: {}".format(ef.multipart))
        assert exp_files, "no file names were generated, this is bug"

        # if we want to attach render to subset, check if we have AOV's
        # in expectedFiles. If so, raise error as we cannot attach AOV
        # (considered to be subset on its own) to another subset
        if render_instance.attachTo:
            assert isinstance(exp_files, list), (
                "attaching multiple AOVs or renderable cameras to "
                "subset is not supported"
            )
        return exp_files

    def add_additional_data(self, data):
        """Add additional data to collected instance.

        This can be overridden by host implementation to add custom
        additional data.

        """
        return data

    def post_collecting_action(self):
        """Execute some code after collection is done.

        This is useful for example for restoring current render layer.

        """
        pass
