import os
import re
import logging
import subprocess
import json
import platform

import opentimelineio as otio
from html2image import Html2Image

import pyblish.api
from openpype.pipeline import publish

class SlateCreator:
    """
    Class that formats and renders an html template
    to use as a slate.

    Html renders as sRGB (or Rec.709 if you want a
    little gamma boost), so rendering will happen
    in .png as intermediate file, while then converted
    to dest cspace using oiio --colorconvert
    attributes syntax.
    
    """
    
    def __init__(
        self,
        staging_dir="",
        staging_subfolder="",
        template_path="",
        resources_path="",
        log=None,
        data={},
        env={}
    ):
        self.staging_dir = ""
        self.template_path = ""
        self.template_res_path = ""
        self.log = None
        self.data = {}
        self.env = {}
        self._template_string = ""
        self._template_string_computed = ""
        self._html_thumb_match_regex = re.compile(
            r"{thumbnail(.*?)}"
        )
        self._html_optional_match_regex = re.compile(
            r"{(.*?)_optional}"
        )
        self._html_path_match_regex = re.compile(
            r"src=\"(.*?)\"|href=\"(.*?)\"|{(thumbnail.*?)}"
        )
        self._html_comment_open_regex = re.compile(
            r"<!--(.*?)"
        )
        self._html_comment_close_regex = re.compile(
            r"(.*?)-->"
        )
        self.platform = platform.system().lower()
        self.exec_ext = ".exe" if self.platform == "windows" else ""
        self.slate_temp_name = "slate_staged"
        self.slate_temp_ext = ".png"
        self.set_logger(logger=log)
        self.set_template_paths(
            template_path,
            resources_path=resources_path
        )
        self.set_data(data)
        self.set_env(env)
        self.set_staging_dir(
            staging_dir,
            subfolder=staging_subfolder
        )
        self.read_template(
            self.template_path,
            self.template_res_path
        )


    def set_logger(self, logger=None):
        """
        Sets the logger for SlateCreator
        """

        if not logger:
            logger = logging.getLogger("SlateCreator")
        
        self.log = logger

        self.log.debug("Logger: '{}'".format(self.log))


    def set_template_paths(self, template_path, resources_path=""):
        """
        Sets template paths if no resources_path is specified
        assumes the same path as template
        """

        if not template_path:
            if self.template_path:
                self.template_path = os.path.normpath(
                    self.template_path
                )
                self.log.debug(
                    "Using previously specified Slate " +
                    "Template path: '{}'".format(
                        self.template_path
                    )
                )
            else:
                self.log.debug("No Slate Template path specified, " +
                "please remember to set it using \'set_template\' " +
                "method or on instance creation!!")
        else:
            self.template_path = os.path.normpath(
                template_path
            )
            self.log.debug(
                "Using newly specified Slate Template path: '{}'".format(
                    self.template_path
                )
            )
        
        if not resources_path:
            if self.template_res_path:
                self.template_res_path = os.path.normpath(
                    self.template_res_path
                )
                self.log.debug(
                    "Using previously specified Slate Resources " +
                    "path: '{}'".format(
                        self.template_res_path
                    )
                )
            else:
                basedir, file = os.path.split(self.template_path)
                self.template_res_path = os.path.normpath(
                    basedir
                )
                self.log.debug(
                    "No Slate Resources Path specified, using "+
                    "same dir as template: '{}'".format(
                        self.template_res_path
                    )
                )
        else:
            self.template_res_path = os.path.normpath(
                resources_path
            )
            self.log.debug(
                "Using newly specified Slate Resources" +
                "path: '{}'".format(
                    self.template_res_path
                )
            )


    def set_data(self, data):
        """
        Copies provided data in an internal dict
        for further use.
        """

        self.data = data.copy()

        self.log.debug(
            "Data: '{}'".format(self.data)
        )


    def set_resolution(self, width, height):
        """
        Change resolution
        """

        self.data["resolution_width"] = width
        self.data["resolution_height"] = height
        self.log.debug(
            "New Resolution set up: '{}x{}'".format(width, height)
        )


    def set_env(self, env={}):
        """
        Sets custom environment for oiio if needed.
        """

        self.env = self.env if self.env else os.environ.copy()
        for k, v in env.items():
            if self.env[k]:
                self.env[k] += os.pathsep + v
            else:
                self.env[k] = v

        self.log.debug("Env: '{}'".format(self.env))


    def set_staging_dir(self, path, subfolder=""):
        """
        Sets staging directory, if subfolder is specified
        it gets appended to staging
        """

        if path:
            staging_dir = os.path.normpath(
                path
            )
        else:
            staging_dir = os.path.normpath(
                os.environ["TEMP"]
            )
        
        if subfolder:
            staging_dir = os.path.join(
                staging_dir,
                subfolder
            )
        
        os.makedirs(staging_dir, exist_ok=True)
        
        self.staging_dir = staging_dir
        
        self.log.debug("Staging dir: '{}'".format(staging_dir))


    def read_template(self, template_path="", resources_path=""):
        """
        Reads template from file and normalizes/absolutizes
        any relative paths in html. The paths gets expanded with
        the resources directory as base. Stores template in an
        internal var for further use.
        """

        if template_path:
            self.template_path = template_path
        if resources_path:
            self.template_res_path = resources_path

        if not self.template_path:
            raise ValueError("Please Specify a template path!")
        if not self.template_res_path:
            raise ValueError("Please Specify a resources path!")

        with open(self.template_path, 'r') as t:
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

                base, file = os.path.split(path)
                
                if self.template_res_path:
                    path_computed = os.path.normpath(
                        os.path.join(
                            self.template_res_path,
                            file
                        )
                    )
                else:
                    path_computed = os.path.normpath(
                        file
                    )
                
                template_computed.append(
                    line.replace(path, path_computed)
                )
            else:
                template_computed.append(line)
        
        template = "".join(template_computed)
        
        self._template_string = template
        
        self.log.debug("Template string: '{}'".format(template))


    def compute_template(
        self,
        process_optionals=True
    ):
        """
        Computes template by substituting template strings.
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
                "Slate Template data is empty, please " + 
                "reread template or check source file."
            )
        
        if process_optionals:
            
            hidden_string = "style=\"display:None;\""

            optional_matches = self._html_optional_match_regex.findall(
                self._template_string
            )

            for m in optional_matches:
                self.data["{}_optional".format(m)] = ""
                if not self.data[m]:
                    self.data["{}_optional".format(m)] = hidden_string
        
        try:
            self._template_string_computed = self._template_string.format(
                **self.data
            )
            self.log.debug("Computed Template string: '{}'".format(
                self._template_string_computed
            ))
        except KeyError as err:
            msg = "Missing {} Key in instance data. ".format(err)
            msg += "Template formatting cannot be completed successfully!"
            self.log.error(msg)
            self._template_string_computed = self._template_string
            raise


    def render_slate(
        self,
        slate_path="",
        slate_specifier="",
        resolution=()
    ):
        """
        Renders out the slate. Templates are rendered using
        Screen color space, usually Rec.709 or sRGB. Any
        HTML that needs to respect color needs to take that
        into account.
        """
        if not slate_path:
            slate_name = "{}{}{}".format(
                self.slate_temp_name,
                slate_specifier,
                self.slate_temp_ext
            )
        else:
            d, f = os.path.split(slate_path)
            if d:
                self.set_staging_dir(d)
            slate_name = f

        data_width = self.data["resolution_width"] or 3840
        data_height = self.data["resolution_height"] or 2160

        if not resolution:
            resolution = (
                data_width,
                data_height
            )
        else:
            self.data["resolution_width"] = resolution[0]
            self.data["resolution_height"] = resolution[1]

        self.compute_template() 

        htimg = Html2Image(output_path=self.staging_dir)

        slate_rendered_path = htimg.screenshot(
            html_str=self._template_string_computed,
            save_as=slate_name,
            size=resolution
        )

        return slate_rendered_path


    def render_image_oiio(
        self,
        input,
        output,
        env={},
        in_args=[],
        out_args=[]
    ):
        """
        renders any image using a subprocess command. args is a list of strings
        returns the completed supprocess
        """
        
        name = os.path.basename(input.replace("\\", "/"))
        env = self.set_env(env) if env else self.env
        
        cmd = []
        cmd.append("oiiotool{}".format(self.exec_ext))
        cmd.extend(in_args)
        cmd.append("-i")
        cmd.append(input)
        cmd.extend(out_args)
        cmd.append("-o")
        cmd.append(output)

        self.log.debug("{}: cmd>{}".format(name, " ".join(cmd)))
        
        res = subprocess.run(
            cmd,
            env=env,
            shell=True if env else False,
            check=True,
            capture_output=True
        )

        return res


    def get_timecode_oiio(self, input, env={}):
        """
        Find timecode using oiio, currently working only on
        images with timecode support, not videos.
        Subtracts 1 frame
        """
        name = os.path.basename(input.replace("\\", "/"))
        env = self.set_env(env) if env else self.env
        cmd = []
        cmd.append("iinfo{}".format(self.exec_ext))
        cmd.append("-v")
        cmd.append(input)
        self.log.debug("{}: cmd>{}".format(name, " ".join(cmd)))
        res = subprocess.run(
            cmd,
            env=env,
            shell=True if env else False,
            check=True,
            capture_output=True
        )

        lines = res.stdout.decode("utf-8").replace(" ", "").splitlines()
        tc = "01:00:00:00"
        
        self.log.debug("{0}: Starting timecode set at: {1}".format(name, tc))
        
        for line in lines:
            if line.lower().find("timecode") > 0:
                vals = line.split(":")
                vals.reverse()
                nums = []
                for i in range(0, 4):
                    nums.append(vals[i])
                nums.reverse()
                tc = ":".join(nums)
                self.log.debug("{0}: New starting timecode Found: {1}".format(name, tc))
                tc_frames = self.timecode_to_frames(tc, self.data["fps"])
                tc_frames -= 1
                tc = self.frames_to_timecode(tc_frames, self.data["fps"])
                self.log.debug("{0}: New timecode for slate: {1}".format(name, tc))
                break

        self.data["timecode"] = tc
        
        return tc


    def get_resolution_ffprobe(self, input, env={}):
        """
        Find input resolution using ffprobe.
        """
        name = os.path.basename(input.replace("\\", "/"))
        env = self.env if not env else env
        cmd = []
        cmd.append("ffprobe{}".format(self.exec_ext))
        cmd.extend(["-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json"])
        cmd.append(input)
        self.log.debug("{}: cmd>{}".format(name, " ".join(cmd)))
        res = subprocess.run(
            cmd,
            env=env,
            shell=True if env else False,
            check=True,
            capture_output=True
        )
        resolution = json.loads(
            res.stdout.decode("utf-8")
        )["streams"][0]
        self.log.debug("{}: File resolution is: {}x{}".format(
            name,
            resolution["width"],
            resolution["height"]))
        
        self.data["resolution_width"] = resolution["width"]
        self.data["resolution_height"] = resolution["height"]
        
        return resolution


    def timecode_to_frames(self, timecode, framerate):
        rt = otio.opentime.from_timecode(timecode, framerate)
        return int(otio.opentime.to_frames(rt))


    def frames_to_timecode(self, frames, framerate):
        rt = otio.opentime.from_frames(frames, framerate)
        return otio.opentime.to_timecode(rt)


    def frames_to_seconds(self, frames, framerate):
        rt = otio.opentime.from_frames(frames, framerate)
        return otio.opentime.to_seconds(rt)


class ExtractSlateGlobal(publish.Extractor):
    """
    Extractor that creates Slate frames using OIIO.

    Slate frames are based on an html template that gets rendered
    using headless chromium. They then get converted using oiio,
    with an ffmpeg fallback (still not implemented).

    It will work only on represenations having `slateGlobal = True` and
    `tags` including `slate`
    """

    label = "Extract Slate Global"
    order = pyblish.api.ExtractorOrder + 0.011
    families = ["slate"]
    hosts = [
        "nuke",
        "maya",
        "shell",
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
            self.log.warning("Slate Global workflow is not active, \
                skipping Global slate extraction...")
            return

        if "representations" not in instance.data:
            self.log.error("No representations to work on!")
            raise ValueError("no items in list.")
        
        repre_ignore_list = [
            "thumbnail",
            "passing"
        ]

        slate_data = instance.data[self._slate_data_name]

        # get pyblish comment and intent
        common_data = slate_data["slate_common_data"]
        common_data["comment"] = instance.context.data.get("comment")
        common_data["intent"].update(instance.context.data.get("intent"))

        # Init SlateCreator Object
        slate = SlateCreator(
            template_path=slate_data["slate_template_path"],
            resources_path=slate_data["slate_template_res_path"],
            log=self.log,
            data=common_data,
            env=slate_data["slate_env"]
        )

        # loop through repres
        for repre in instance.data["representations"]:
            if repre["name"] in repre_ignore_list:
                self.log.debug("Representation '{}' was ignored.".format(
                    repre["name"]
                ))
                continue

            # check if repre is a sequence
            isSequence = False
            check_file = repre["files"]
            if isinstance(check_file, list):
                check_file = check_file[0]
                isSequence = True
            
            file_path = os.path.normpath(
                os.path.join(
                    repre["stagingDir"],
                    check_file
                )
            )

            filename, specname, ext = check_file.split(".")
            timecode = slate.get_timecode_oiio(file_path)
            resolution = slate.get_resolution_ffprobe(file_path)

            # if sequence render out a slate before first frame
            # else sequence find matching tags and transfer
            # also constructs final slate name and metadata
            if isSequence:
                frame_start = int(repre["frameStart"]) - 1
                frame_end = len(repre["files"]) + frame_start
                output_name = "{}.{}.{}".format(
                    filename,
                    frame_start,
                    ext
                )
                repre_match = instance.data["family"]
            else:
                frame_start = int(repre["frameStart"]) 
                frame_end = int(repre["frameEnd"]) 
                output_name = "{}_{}_slate.png".format(
                    filename,
                    repre["name"]
                )
                for tag in repre["tags"]:
                    for profile in slate_data["slate_profiles"]:
                        if tag in profile["families"]:
                            repre_match = tag

            for profile in slate_data["slate_profiles"]:
                if repre_match in profile["families"]:
                    oiio_profile = profile
                else: 
                    oiio_profile = {
                        "families": [],
                        "hosts": [],
                        "oiio_args": {
                            "input": [],
                            "output": []
                        }
                    }
                # add timecode to oiio output args
                oiio_profile["oiio_args"]["output"].extend([
                    "--attrib:type=timecode",
                    "smpte:TimeCode",
                    "\"{}\"".format(timecode)
                ])

            # Data Layout and preparation in instance
            slate_repre_data = slate_data["slate_repre_data"][repre["name"]] = {
                "family_match": repre_match or "",
                "frameStart": int(repre["frameStart"]),
                "frameEnd": frame_end,
                "real_frameStart": frame_start,
                "resolution_width": int(resolution["width"]),
                "resolution_height": int(resolution["height"]),
                "stagingDir": repre["stagingDir"],
                "slate_file": output_name,
                "thumbnail": instance.data["thumbnail"],
                "timecode": timecode
            }
            slate.data.update(slate_repre_data)
            slate.data.update(oiio_profile)

            # set properties for rendering
            slate.set_resolution(
                slate.data["resolution_width"],
                slate.data["resolution_height"]
            )
            slate.set_staging_dir(slate.data["stagingDir"])

            # render slate
            temp_slate = slate.render_slate(
                slate_specifier="_{}".format(repre["name"])
            )

            slate_final_path = os.path.normpath(
                os.path.join(
                    slate.data["stagingDir"],
                    slate.data["slate_file"]
                )
            )

            # convert slate to final name and format
            slate.render_image_oiio(
                temp_slate[0],
                slate_final_path,
                in_args=slate.data["oiio_args"]["input"],
                out_args=slate.data["oiio_args"]["output"]
            )
            os.remove(temp_slate[0])

            # update repres and instance
            if isSequence:
                repre["files"].insert(0, slate.data["slate_file"])
                repre["frameStart"] = slate.data["real_frameStart"]
                self.log.debug(
                    "Added {} to {} representation file list.".format(
                        slate.data["slate_file"],
                        repre["name"]
                    )
                )
            else:
                if "slateFrames" not in instance.data:
                    instance.data["slateFrames"] = {
                        "*": slate_final_path
                    }
                else:
                    instance.data["slateFrames"].update({
                        output_name: slate_final_path
                    })
                
                self.log.debug("SlateFrames: {}".format(
                    instance.data["slateFrames"]
                ))
