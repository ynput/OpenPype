# -*- coding: utf-8 -*-
"""Collect render template.

TODO: use @dataclass when times come.

"""
from abc import abstractmethod

import attr
import six

import pyblish.api

from openpype.pipeline import legacy_io

from .abstract_metaplugins import AbstractMetaContextPlugin


@attr.s
class RenderInstance(object):
    """Data collected by collectors.

    This data class later on passed to collected instances.
    Those attributes are required later on.

    """

    # metadata
    version = attr.ib()  # instance version
    time = attr.ib()  # time of instance creation (get_formatted_current_time)
    source = attr.ib()  # path to source scene file
    label = attr.ib()  # label to show in GUI
    subset = attr.ib()  # subset name
    asset = attr.ib()  # asset name (AVALON_ASSET)
    attachTo = attr.ib()  # subset name to attach render to
    setMembers = attr.ib()  # list of nodes/members producing render output
    publish = attr.ib()  # bool, True to publish instance
    name = attr.ib()  # instance name

    # format settings
    resolutionWidth = attr.ib()  # resolution width (1920)
    resolutionHeight = attr.ib()  # resolution height (1080)
    pixelAspect = attr.ib()  # pixel aspect (1.0)

    # time settings
    frameStart = attr.ib()  # start frame
    frameEnd = attr.ib()  # start end
    frameStep = attr.ib()  # frame step

    handleStart = attr.ib(default=None)  # start frame
    handleEnd = attr.ib(default=None)  # start frame

    # for software (like Harmony) where frame range cannot be set by DB
    # handles need to be propagated if exist
    ignoreFrameHandleCheck = attr.ib(default=False)

    # --------------------
    # With default values
    # metadata
    renderer = attr.ib(default="")  # renderer - can be used in Deadline
    review = attr.ib(default=False)  # generate review from instance (bool)
    priority = attr.ib(default=50)  # job priority on farm

    family = attr.ib(default="renderlayer")
    families = attr.ib(default=["renderlayer"])  # list of families

    # format settings
    multipartExr = attr.ib(default=False)  # flag for multipart exrs
    convertToScanline = attr.ib(default=False)  # flag for exr conversion

    tileRendering = attr.ib(default=False)  # bool: treat render as tiles
    tilesX = attr.ib(default=0)  # number of tiles in X
    tilesY = attr.ib(default=0)  # number of tiles in Y

    # submit_publish_job
    toBeRenderedOn = attr.ib(default=None)
    deadlineSubmissionJob = attr.ib(default=None)
    anatomyData = attr.ib(default=None)
    outputDir = attr.ib(default=None)
    context = attr.ib(default=None)

    @frameStart.validator
    def check_frame_start(self, _, value):
        """Validate if frame start is not larger then end."""
        if value > self.frameEnd:
            raise ValueError("frameStart must be smaller "
                             "or equal then frameEnd")

    @frameEnd.validator
    def check_frame_end(self, _, value):
        """Validate if frame end is not less then start."""
        if value < self.frameStart:
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


@six.add_metaclass(AbstractMetaContextPlugin)
class AbstractCollectRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Render"
    sync_workfile_version = False

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(AbstractCollectRender, self).__init__(*args, **kwargs)
        self._file_path = None
        self._asset = legacy_io.Session["AVALON_ASSET"]
        self._context = None

    def process(self, context):
        """Entry point to collector."""
        self._context = context
        for instance in context:
            # make sure workfile instance publishing is enabled
            try:
                if "workfile" in instance.data["families"]:
                    instance.data["publish"] = True
                if "renderFarm" in instance.data["families"]:
                    instance.data["remove"] = True
            except KeyError:
                # be tolerant if 'families' is missing.
                pass

        self._file_path = context.data["currentFile"].replace("\\", "/")

        render_instances = self.get_instances(context)
        for render_instance in render_instances:
            exp_files = self.get_expected_files(render_instance)
            assert exp_files, "no file names were generated, this is bug"

            # if we want to attach render to subset, check if we have AOV's
            # in expectedFiles. If so, raise error as we cannot attach AOV
            # (considered to be subset on its own) to another subset
            if render_instance.attachTo:
                assert isinstance(exp_files, list), (
                    "attaching multiple AOVs or renderable cameras to "
                    "subset is not supported"
                )

            frame_start_render = int(render_instance.frameStart)
            frame_end_render = int(render_instance.frameEnd)
            if (render_instance.ignoreFrameHandleCheck or
                    int(context.data['frameStartHandle']) == frame_start_render
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
                "handleStart": handle_start,
                "handleEnd": handle_end,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartHandle": frame_start_handle,
                "frameEndHandle": frame_end_handle,
                "byFrameStep": int(render_instance.frameStep),

                "author": context.data["user"],
                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "expectedFiles": exp_files,
            }
            if self.sync_workfile_version:
                data["version"] = context.data["version"]

            # add additional data
            data = self.add_additional_data(data)
            render_instance_dict = attr.asdict(render_instance)

            instance = context.create_instance(render_instance.name)
            instance.data["label"] = render_instance.label
            instance.data.update(render_instance_dict)
            instance.data.update(data)

        self.post_collecting_action()

    @abstractmethod
    def get_instances(self, context):
        """Get all renderable instances and their data.

        Args:
            context (pyblish.api.Context): Context object.

        Returns:
            list of :class:`RenderInstance`: All collected renderable instances
                (like render layers, write nodes, etc.)

        """
        pass

    @abstractmethod
    def get_expected_files(self, render_instance):
        """Get list of expected files.

        Returns:
            list: expected files. This can be either simple list of files with
                their paths, or list of dictionaries, where key is name of AOV
                for example and value is list of files for that AOV.

        Example::

            ['/path/to/file.001.exr', '/path/to/file.002.exr']

            or as dictionary:

            [
                {
                    "beauty": ['/path/to/beauty.001.exr', ...],
                    "mask": ['/path/to/mask.001.exr']
                }
            ]

        """
        pass

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
