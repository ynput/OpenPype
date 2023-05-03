import os
import re
import logging
import tempfile
import platform

import opentimelineio as otio
import pyblish.api
from html2image import Html2Image

from openpype.lib import (
    get_oiio_tools_path,
    get_ffprobe_streams,
    get_chrome_tool_path,
    run_subprocess,
)
from openpype.pipeline import publish


def timecode_to_frames(timecode, framerate):
    rt = otio.opentime.from_timecode(timecode, framerate)
    return int(otio.opentime.to_frames(rt))


def frames_to_timecode(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_timecode(rt)


def frames_to_seconds(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_seconds(rt)


class SlateCreator:
    """Class that formats and renders an html template to use as a slate.

    Html renders as sRGB (or Rec.709 if you want a little gamma boost), so
    rendering will happen in .png as intermediate file, while then converted
    to dest cspace using oiio --colorconvert attributes syntax.

    """

    def __init__(
        self,
        staging_dir="",
        staging_subfolder="",
        template_path="",
        resources_path="",
        data=None,
    ):
        self.data = data.copy() if data else {}
        self.log = logging.getLogger(self.__class__.__name__)

        self._template_string = ""
        self._template_string_computed = ""
        self._html_thumb_match_regex = re.compile(r"{thumbnail(.*?)}")
        self._html_optional_match_regex = re.compile(r"{(.*?)_optional}")
        self._html_path_match_regex = re.compile(
            r"src=\"(.*?)\"|href=\"(.*?)\"|{(thumbnail.*?)}"
        )
        self._html_comment_open_regex = re.compile(r"<!--(.*?)")
        self._html_comment_close_regex = re.compile(r"(.*?)-->")
        self.platform = platform.system().lower()
        self.exec_ext = ".exe" if self.platform == "windows" else ""
        self.slate_temp_name = "slate_staged"
        self.slate_temp_ext = ".png"

        self.set_template_paths(template_path, resources_path=resources_path)
        self.set_staging_dir(staging_dir, subfolder=staging_subfolder)
        self.read_template()
        self.task_filter = []

    def set_template_paths(self, template_path, resources_path=""):
        """Sets path of html slate template and CSS resources."""

        if template_path:
            self.template_path = os.path.normpath(template_path)
            self.log.debug(
                "Using newly specified Slate Template path: '{}'".format(
                    self.template_path
                )
            )
        elif self.template_path:
            self.template_path = os.path.normpath(self.template_path)
            self.log.debug(
                "Using previously specified Slate Template path: '{}'".format(
                    self.template_path
                )
            )
        else:
            self.log.debug(
                "No Slate Template path specified, please remember to set it using"
                "'set_template' method or on instance creation!!"
            )

        if resources_path:
            self.template_res_path = os.path.normpath(resources_path)
            self.log.debug(
                "Using newly specified Slate Resources path: '{}'".format(
                    self.template_res_path
                )
            )
        elif self.template_res_path:
            self.template_res_path = os.path.normpath(
                self.template_res_path
            )
            self.log.debug(
                "Using previously specified Slate Resources path: '{}'".format(
                    self.template_res_path
                )
            )
        else:
            basedir = os.path.basename(self.template_path)
            self.template_res_path = os.path.normpath(basedir)
            self.log.debug(
                "No Slate Resources Path specified, using same dir as template: '{}'".format(
                    self.template_res_path
                )
            )

    def set_resolution(self, width, height):
        self.data["resolution_width"] = width
        self.data["resolution_height"] = height
        self.log.debug("New Resolution set up: '{}x{}'".format(width, height))

    def set_staging_dir(self, path, subfolder=""):
        if path:
            staging_dir = os.path.normpath(path)
        else:
            staging_dir = tempfile.gettempdir()

        if subfolder:
            staging_dir = os.path.join(staging_dir, subfolder)

        if not os.path.exists(staging_dir):
            os.makedirs(staging_dir)

        self.staging_dir = staging_dir

        self.log.debug("Staging dir: '{}'".format(staging_dir))

    def read_template(self, template_path=None, resources_path=None):
        """
        Reads template from file and normalizes/absolutizes
        any relative paths in html. The paths gets expanded with
        the resources directory as base. Stores template in an
        internal var for further use.
        """
        template_path = template_path or self.template_path
        if not template_path:
            raise ValueError("Please Specify a template path!")

        resources_path = resources_path or self.template_res_path
        if not resources_path:
            raise ValueError("Please Specify a resources path!")

        with open(template_path, "r") as t:
            template = t.readlines()

        template_computed = []
        html_comment_open = False

        for line in template:

            if self._html_comment_open_regex.search(line) is not None:
                html_comment_open = True

            if self._html_comment_close_regex.search(line) is not None:
                html_comment_open = False
                continue

            if html_comment_open:
                continue

            search = self._html_path_match_regex.search(line)

            if search is not None:

                path_tuple = self._html_path_match_regex.findall(line)[0]
                path = ""

                for element in path_tuple:
                    if element:
                        path = element
                        break

                if not path.find("{"):
                    template_computed.append(line)
                    continue

                _, file = os.path.split(path)

                if self.template_res_path:
                    path_computed = os.path.normpath(
                        os.path.join(self.template_res_path, file)
                    )
                else:
                    path_computed = os.path.normpath(file)

                template_computed.append(line.replace(path, path_computed))
            else:
                template_computed.append(line)

        template = "".join(template_computed)

        self._template_string = template

        self.log.debug("Template string: '{}'".format(template))

    def compute_template(self, process_optionals=True):
        """Compute HTML template by substituting template strings.

        Needs keys to be at the root of data dict, no support
        for nested dicts for now, just for lists.
        Keys in template with "_optional" are substituted
        with "display:None" in the style property, this
        enables to hide selectively any block if any
        corresponding key is empty.
        example: {scope} -> {scope_optional}
        """

        if not self._template_string:
            raise ValueError(
                "Slate Template data is empty, please reread template or check source "
                "file."
            )

        if process_optionals:
            hidden_string = 'style="display:None;"'

            optional_matches = self._html_optional_match_regex.findall(
                self._template_string
            )

            for match in optional_matches:
                self.data["{}_optional".format(match)] = ""
                if not self.data[match]:
                    self.data["{}_optional".format(match)] = hidden_string

        try:
            self._template_string_computed = self._template_string.format(
                **self.data
            )
            self.log.debug(
                "Computed Template string: '{}'".format(
                    self._template_string_computed
                )
            )
        except KeyError as err:
            msg = "Missing {} key in instance data. ".format(err)
            msg += "Template formatting cannot be completed successfully!"
            self.log.error(msg)
            self._template_string_computed = self._template_string
            raise

    def render_slate(self, slate_path="", slate_specifier="", resolution=None):
        """
        Renders out the slate. Templates are rendered using
        Screen color space, usually Rec.709 or sRGB. Any
        HTML that needs to respect color needs to take that
        into account.
        """
        if slate_path:
            base_dir, filename = os.path.split(slate_path)
            if base_dir:
                self.set_staging_dir(base_dir)
            slate_name = filename
        else:
            slate_name = "{}{}{}".format(
                self.slate_temp_name, slate_specifier, self.slate_temp_ext
            )

        if resolution:
            self.data["resolution_width"] = resolution[0]
            self.data["resolution_height"] = resolution[1]
        else:
            data_width = self.data["resolution_width"] or 3840
            data_height = self.data["resolution_height"] or 2160
            resolution = (data_width, data_height)

        self.compute_template()

        browser_executable = get_chrome_tool_path()
        self.log.info("Render slate using html2image at '%s'.", self.staging_dir)
        self.log.info("Using resolution '%s'.", resolution)
        hti = Html2Image(browser_executable=browser_executable, output_path=self.staging_dir)

        slate_rendered_paths = hti.screenshot(
            html_str=self._template_string_computed,
            save_as=slate_name,
            size=resolution,
        )

        return slate_rendered_paths[0]

    def render_image_oiio(self, input, output, in_args=None, out_args=None):
        """Call oiiotool to convert one image to another."""
        cmd = [get_oiio_tools_path()]
        cmd.extend(in_args or [])
        cmd.extend(["-i", input])
        cmd.extend(out_args or [])
        cmd.extend(["-o", output])
        self.log.info("Running: {}".format(" ".join(cmd)))
        try:
            run_subprocess(cmd, logger=self.log)
        except TypeError as error:
            raise TypeError(
                "Error creating '{}' due to: {}".format(output, error)
            )

    def get_timecode_oiio(self, input, tc_frame=1001):
        """Find timecode using OpenImageIO iinfo tool.

        Only images with timecode supported, not videos.

        """
        name = os.path.basename(input.replace("\\", "/"))
        cmd = [get_oiio_tools_path(tool="iinfo"), "-v", input]
        self.log.info("Running: {}".format(" ".join(cmd)))
        try:
            output = run_subprocess(cmd, logger=self.log)
        except TypeError as error:
            raise TypeError(
                "Error finding timecode of '{}' due to: {}".format(input, error)
            )

        tc = frames_to_timecode(int(tc_frame), self.data["fps"])
        self.log.debug("{0}: Starting timecode set at: {1}".format(name, tc))

        lines = output.splitlines()
        for line in lines:
            if line.lower().find("timecode") > 0:
                vals = line.split(":")
                vals.reverse()
                nums = vals[0:4]
                nums.reverse()
                tc = ":".join(nums)
                break

        self.log.debug("{0}: New starting timecode found: {1}".format(name, tc))
        tc_frames = timecode_to_frames(tc, self.data["fps"])
        # Subtracts one frame
        # TODO: Explain why?
        tc_frames -= 1
        tc = frames_to_timecode(tc_frames, self.data["fps"])

        self.log.debug("{0}: New timecode for slate: {1}".format(name, tc))
        self.data["timecode"] = tc

        return tc

    def get_resolution_ffprobe(self, input):
        """Find input resolution using ffprobe."""
        try:
            streams = get_ffprobe_streams(input, self.log)
        except Exception as exc:
            raise AssertionError(
                (
                    'FFprobe couldn\'t read information about input file: "{}".'
                    " Error message: {}"
                ).format(input, str(exc))
            )

        # Try to find first stream with defined 'width' and 'height'
        width = None
        height = None
        for stream in streams:
            if "width" in stream and "height" in stream:
                width = int(stream["width"])
                height = int(stream["height"])
                break

        # Raise exception of any stream didn't define input resolution
        if width is None:
            raise AssertionError(
                (
                    "FFprobe couldn't read resolution from input file: '{}'"
                ).format(input)
            )

        return (width, height)


class ExtractSlateGlobal(publish.Extractor):
    """
    Extractor that creates slate frames from an HTML template using OIIO.

    Slate frames are based on an html template that gets rendered
    using headless chrome/chromium. They then get converted using oiio,
    with an ffmpeg fallback (still not implemented).

    It will work only on represenations having `slateGlobal = True` and
    `tags` including `slate`
    """

    label = "Extract Slate Global"
    order = pyblish.api.ExtractorOrder + 0.0305
    families = ["slate"]
    hosts = [
        "nuke",
        "maya",
        "shell",
        "houdini"
        # "hiero",
        # "premiere",
        # "harmony",
        # "traypublisher",
        # "standalonepublisher",
        # "fusion",
        # "tvpaint",
        # "resolve",
        # "webpublisher",
        # "aftereffects",
        # "flame",
        # "unreal"
    ]

    _slate_data_name = "slateGlobal"

    def process(self, instance):

        if self._slate_data_name not in instance.data:
            self.log.warning(
                "Slate Global workflow is not active, \
                skipping Global slate extraction..."
            )
            return

        if "representations" not in instance.data:
            self.log.error("No representations to work on!")
            raise ValueError("no items in list.")

        repre_ignore_list = ["thumbnail", "passing"]

        slate_data = instance.data[self._slate_data_name]

        # get pyblish comment and intent
        common_data = slate_data["slate_common_data"]
        common_data["comment"] = instance.context.data.get("comment") or "-"
        intent = instance.context.data.get("intent")
        if not isinstance(intent, dict):
            intent = {
                "label": intent,
                "value": intent
            }
        common_data["intent"] = intent

        # Init SlateCreator Object
        slate = SlateCreator(
            template_path=slate_data["slate_template_path"],
            resources_path=slate_data["slate_template_res_path"],
            data=common_data,
        )

        # loop through repres
        for repre in instance.data["representations"]:
            if repre["name"] in repre_ignore_list:
                self.log.debug(
                    "Representation '{}' was ignored.".format(repre["name"])
                )
                continue

            # loop through repres for thumbnail
            thumbnail_path = ""
            for thumb_repre in instance.data["representations"]:
                if thumb_repre["name"] == "thumbnail":
                    thumbnail_path = os.path.join(
                        thumb_repre["stagingDir"], thumb_repre["files"]
                    )

            # check if repre is a sequence
            is_sequence = False
            check_file = repre["files"]
            if isinstance(check_file, list):
                check_file = check_file[0]
                is_sequence = True

            file_path = os.path.normpath(
                os.path.join(repre["stagingDir"], check_file)
            )

            # if sequence render out a slate before first frame
            # else sequence find matching tags and transfer
            # also constructs final slate name and metadata
            if is_sequence:
                filename, _frame, ext = check_file.split(".")
                frame_start = int(repre["frameStart"]) - 1
                frame_end = len(repre["files"]) + frame_start
                output_name = "{}.{}.{}".format(
                    filename,
                    str(frame_start).zfill(int(common_data["frame_padding"])),
                    ext,
                )
                thumbnail_path = os.path.join(
                    repre["stagingDir"],
                    "{}_slate_thumb.png".format(repre["name"]),
                ).replace("\\", "/")
                slate.render_image_oiio(
                    file_path.replace("\\", "/"), thumbnail_path
                )
                repre_match = instance.data["family"]
            else:
                frame_start = int(repre["frameStart"])
                frame_end = int(repre["frameEnd"])
                output_name = "{}_slate_temp.png".format(repre["name"])
                for tag in repre["tags"]:
                    for profile in slate_data["slate_profiles"]:
                        if tag in profile["families"]:
                            repre_match = tag

            timecode = slate.get_timecode_oiio(
                file_path, tc_frame=int(repre["frameStart"])
            )
            width, height = slate.get_resolution_ffprobe(file_path)

            for profile in slate_data["slate_profiles"]:
                if repre_match in profile["families"]:
                    oiio_profile = profile
                else:
                    oiio_profile = {
                        "families": [],
                        "hosts": [],
                        "oiio_args": {"input": [], "output": []},
                    }
                # add timecode to oiio output args
                oiio_profile["oiio_args"]["output"].extend(
                    [
                        "--attrib:type=timecode",
                        "smpte:TimeCode",
                        '"{}"'.format(timecode),
                    ]
                )

            # Data Layout and preparation in instance
            slate_repre_data = slate_data["slate_repre_data"][repre["name"]] = {
                "family_match": repre_match or "",
                "frameStart": int(repre["frameStart"]),
                "frameEnd": frame_end,
                "frameStartHandle": instance.data.get("frameStartHandle", None),
                "frameEndHandle": instance.data.get("frameEndHandle", None),
                "real_frameStart": frame_start,
                "resolution_width": width,
                "resolution_height": height,
                "stagingDir": repre["stagingDir"],
                "slate_file": output_name,
                "thumbnail": thumbnail_path,
                "timecode": timecode,
            }
            slate.data.update(slate_repre_data)
            slate.data.update(oiio_profile)

            # set properties for rendering
            slate.set_resolution(
                slate.data["resolution_width"], slate.data["resolution_height"]
            )
            slate.set_staging_dir(slate.data["stagingDir"])

            # render slate
            temp_slate = slate.render_slate(
                slate_path="{}_slate.png".format(repre["name"])
            )

            slate_final_path = os.path.normpath(
                os.path.join(slate.data["stagingDir"], slate.data["slate_file"])
            )

            slate.render_image_oiio(
                temp_slate,
                slate_final_path,
                in_args=oiio_profile["oiio_args"].get("input") or [],
                out_args=oiio_profile["oiio_args"].get("output") or [],
            )

            # update repres and instance
            if is_sequence:
                repre["files"].insert(0, slate.data["slate_file"])
                repre["frameStart"] = slate.data["real_frameStart"]
                self.log.debug(
                    "Added {} to {} representation file list.".format(
                        slate.data["slate_file"], repre["name"]
                    )
                )
            else:
                if "slateFrames" not in instance.data:
                    instance.data["slateFrames"] = {"*": slate_final_path}
                else:
                    instance.data["slateFrames"].update(
                        {repre["name"]: slate_final_path}
                    )
                instance.data["slateFrame"] = slate_final_path
                self.log.debug(
                    "SlateFrames: {}".format(instance.data["slateFrames"])
                )
