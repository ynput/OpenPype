import os
import pyblish.api
import pype.api


class ExtractScaledThumbnails(pyblish.api.InstancePlugin):
    """Create scaled thumbnails for GUIs like loader etc.

    Scaled thumbnails creation is based on data in `output_data` attribute.
    The dictionary `output_data` store additional filename ending and
    filters for ffmpeg.

    Example:
        "small": {
            "file_end": "S",
            "filters": ["scale=160:-1"]
        }

        "small" - key is used to store result under represetation
        "file_end"  - is distinguishing part for files.
                    - "S" means that source thumbnail "myasset_thumbnail.jpg"
                        will be converted to "myasset_thumbnail_S.jpg"
        "filters"   - should contain filters for ffmpeg, key is `scale` filter
                        which is used to render thumbnails with different
                        resolution.
                    - "160:-1" will render thumbnail with 160px width and keep
                        aspect ratio of source image
    """

    order = pyblish.api.ExtractorOrder + 0.499
    label = "Extract scaled thumbnails"

    optional = True
    active = True
    hosts = ["nuke", "maya", "shell"]
    # Default setting for output data
    output_data = {
        "small": {
            "file_end": "S",
            "filters": ["scale=160:-1"]
        },
        "middle": {
            "file_end": "M",
            "filters": ["scale=320:-1"]
        },
        "large": {
            "file_end": "L",
            "filters": ["scale=1024:-1"]
        }
    }

    def process(self, instance):
        for repre in instance.data["representations"]:
            name = repre.get("name", "")
            if name:
                name = " <{}>".format(name)
            self.log.debug("Checking repre{}: {}".format(name, repre))
            # Skip if thumbnail not in tags
            tags = repre.get("tags") or []
            if (
                "thumbnail" not in tags and
                not repre.get("thumbnail") # backwards compatibility
            ):
                continue

            # skip if files are not set or empty
            files = repre.get("files")
            if not files:
                continue

            orig_filename = None
            if isinstance(files, (str, unicode)):
                orig_filename = files
            elif isinstance(files, list):
                orig_filename = files[0]
            else:
                self.log.debug((
                    "Original `files`{} have invalid type \"{}\" on repre {}"
                ).format(name, str(type(files)), str(repre)))
                continue

            staging_dir = repre["stagingDir"]
            full_input_path = os.path.join(staging_dir, orig_filename)

            orig_basename, orig_ext = os.path.splitext(orig_filename)
            thumbnail_data = {}

            _input_args = []
            # Overrides output file
            _input_args.append("-y")
            # Set input path
            _input_args.append("-i \"{}\"".format(full_input_path))

            ffmpeg_path = os.path.join(
                os.environ.get("FFMPEG_PATH", ""), "ffmpeg"
            )

            for output_type, single_data in self.output_data.items():
                # DEBUG remove after testing!
                self.log.debug(output_type)
                file_end = single_data["file_end"]
                in_filters = single_data["filters"]

                ffmpeg_filters = []
                if in_filters:
                    ffmpeg_filters.append("-vf")
                    ffmpeg_filters.extend([fil for fil in in_filters])

                # copy _input_args
                input_args = [arg for arg in _input_args]
                input_args.extend(ffmpeg_filters)

                output_args = []
                filename = "{}_{}{}".format(
                    orig_basename, file_end, orig_ext
                )
                full_output_path = os.path.join(staging_dir, filename)
                output_args.append("\"{}\"".format(full_output_path))

                mov_args = [
                    ffmpeg_path,
                    " ".join(input_args),
                    " ".join(output_args)
                ]
                subprcs_cmd = " ".join(mov_args)

                self.log.debug("Executing: {}".format(subprcs_cmd))
                output = pype.api.subprocess(subprcs_cmd)
                self.log.debug("Output: {}".format(output))

                # Store data for integrator
                thumbnail_data[output_type] = {
                    "path": full_output_path,
                    "filename_append": file_end
                }

            repre["thumbnail_data"] = thumbnail_data
