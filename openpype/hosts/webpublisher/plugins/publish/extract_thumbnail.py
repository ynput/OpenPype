import os
import shutil

import pyblish.api
from openpype.lib import (
    get_ffmpeg_tool_path,

    run_subprocess,

    get_transcode_temp_directory,
    convert_input_paths_for_ffmpeg,
    should_convert_for_ffmpeg
)


class ExtractThumbnail(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from input using ffmpeg."""

    label = "Extract Thumbnail"
    order = pyblish.api.ExtractorOrder
    families = [
        "render",
        "image"
    ]
    hosts = ["webpublisher"]
    targets = ["filespublish"]

    def process(self, instance):
        self.log.info("subset {}".format(instance.data['subset']))

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
            self.log.info("Input filepath: {}".format(full_input_path))

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
            while filename.endswith("."):
                filename = filename[:-1]
            thumbnail_filename = filename + "_thumbnail.jpg"
            full_output_path = os.path.join(stagingdir, thumbnail_filename)

            self.log.info("output {}".format(full_output_path))

            ffmpeg_args = [
                get_ffmpeg_tool_path("ffmpeg"),
                "-y",
                "-i", full_input_path,
                "-vframes", "1",
                full_output_path
            ]

            # run subprocess
            self.log.debug("{}".format(" ".join(ffmpeg_args)))
            try:  # temporary until oiiotool is supported cross platform
                run_subprocess(
                    ffmpeg_args, logger=self.log
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
                "files": thumbnail_filename,
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

    def _get_filtered_repres(self, instance):
        filtered_repres = []
        repres = instance.data.get("representations") or []
        for repre in repres:
            self.log.debug(repre)
            tags = repre.get("tags") or []
            # Skip instance if already has thumbnail representation
            if "thumbnail" in tags:
                return []

            if "review" not in tags:
                continue

            if not repre.get("files"):
                self.log.info((
                    "Representation \"{}\" don't have files. Skipping"
                ).format(repre["name"]))
                continue

            filtered_repres.append(repre)
        return filtered_repres
