import os

import pyblish.api
from openpype.pipeline import ( 
    legacy_io,
    KnownPublishError
)
from openpype.lib import (
    get_ffmpeg_tool_path,
    get_oiio_tools_path,

    filter_profiles,
    run_subprocess,
    path_to_subprocess_arg,

    get_transcode_temp_directory,
    convert_input_paths_for_ffmpeg,
    should_convert_for_ffmpeg
)

import shutil


class ExtractThumbnail(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Thumbnail"
    order = pyblish.api.ExtractorOrder
    families = [
        "imagesequence", "render", "render2d",
        "source", "plate", "take"
    ]
    hosts = ["shell", "fusion", "resolve"]
    enabled = False

    # presetable attribute
    ffmpeg_args = None
    oiio_args = None

    def process(self, instance):
        task_name = instance.data.get("task", legacy_io.Session["AVALON_TASK"])
        host_name = legacy_io.Session["AVALON_APP"]
        family = instance.data["family"]
        filtering_criteria = {
            "hosts": host_name,
            "families": family,
            "tasks": task_name
        }
        profile = filter_profiles(self.profiles, filtering_criteria,
                                  logger=self.log)
        if not profile:
            return

        oiio_path = get_oiio_tools_path()
        # Raise an exception when oiiotool is not available

        if not os.path.exists(oiio_path):
            KnownPublishError(
                "OpenImageIO tool is not available on this machine."
            )
        self.log.info("subset {}".format(instance.data['subset']))

        # skip crypto passes.
        # TODO: This is just a quick fix and has its own side-effects - it is
        #       affecting every subset name with `crypto` in its name.
        #       This must be solved properly, maybe using tags on
        #       representation that can be determined much earlier and
        #       with better precision.
        if 'crypto' in instance.data['subset'].lower():
            self.log.info("Skipping crypto passes.")
            return

        # Skip if review not set.
        if not instance.data.get("review", True):
            self.log.info("Skipping - no review set on instance.")
            return

        filtered_repres = self._get_filtered_repres(instance)

        for repre in filtered_repres:
            repre_files = repre["files"]
            if not isinstance(repre_files, (list, tuple)):
                input_file = repre_files
            else:
                file_index = int(float(len(repre_files)) * 0.5)
                input_file = repre_files[file_index]

            stagingdir = os.path.normpath(repre["stagingDir"])

            full_input_path = os.path.join(stagingdir, input_file)
            self.log.info("input {}".format(full_input_path))

            do_convert = should_convert_for_ffmpeg(full_input_path)
            # If result is None the requirement of conversion can't be
            #   determined
            if do_convert is None:
                self.log.info((
                    "Can't determine if representation requires conversion."
                    " Skipped."
                ))
                continue

            # Do conversion if needed
            #   - change staging dir of source representation
            #   - must be set back after output definitions processing
            convert_dir = None
            if do_convert:
                convert_dir = get_transcode_temp_directory()
                filename = os.path.basename(full_input_path)
                convert_input_paths_for_ffmpeg(
                    [full_input_path],
                    convert_dir,
                    self.log
                )
                full_input_path = os.path.join(convert_dir, filename)

            filename = os.path.splitext(input_file)[0]
            if not filename.endswith('.'):
                filename += "."
            jpeg_file = filename + "jpg"
            full_output_path = os.path.join(stagingdir, jpeg_file)

            self.log.info("output {}".format(full_output_path))

            ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")
            ffmpeg_args = self.ffmpeg_args or {}

            jpeg_items = []
            jpeg_items.append(path_to_subprocess_arg(ffmpeg_path))
            # override file if already exists
            jpeg_items.append("-y")
            # use same input args like with mov
            jpeg_items.extend(ffmpeg_args.get("input") or [])
            # input file
            jpeg_items.append("-i {}".format(
                path_to_subprocess_arg(full_input_path)
            ))
            # output arguments from presets
            jpeg_items.extend(ffmpeg_args.get("output") or [])

            # If its a movie file, we just want one frame.
            if repre["ext"] == "mov":
                jpeg_items.append("-vframes 1")

            # output file
            jpeg_items.append(path_to_subprocess_arg(full_output_path))
            subprocess_command = " ".join(jpeg_items)

            # run subprocess
            self.log.debug("{}".format(subprocess_command))
            try:  # temporary until oiiotool is supported cross platform
                run_subprocess(
                    subprocess_command, shell=True, logger=self.log
                )
            except RuntimeError as exp:
                if "Compression" in str(exp):
                    self.log.debug(
                        "Unsupported compression on input files. Skipping!!!"
                    )
                    return
                self.log.warning("Conversion crashed", exc_info=True)
                raise

            new_repre = {
                "name": "thumbnail",
                "ext": "jpg",
                "files": jpeg_file,
                "stagingDir": stagingdir,
                "thumbnail": True,
                "tags": ["thumbnail"]
            }

            # adding representation
            self.log.debug("Adding: {}".format(new_repre))
            instance.data["representations"].append(new_repre)

            # Cleanup temp folder
            if convert_dir is not None and os.path.exists(convert_dir):
                shutil.rmtree(convert_dir)

            # Create only one representation with name 'thumbnail'
            # TODO maybe handle way how to decide from which representation
            #   will be thumbnail created
            break

    def _get_filtered_repres(self, instance):
        filtered_repres = []
        src_repres = instance.data.get("representations") or []
        for repre in src_repres:
            self.log.debug(repre)
            tags = repre.get("tags") or []
            valid = "review" in tags or "thumb-nuke" in tags
            if not valid:
                continue

            if not repre.get("files"):
                self.log.info((
                    "Representation \"{}\" don't have files. Skipping"
                ).format(repre["name"]))
                continue

            filtered_repres.append(repre)
        return filtered_repres
