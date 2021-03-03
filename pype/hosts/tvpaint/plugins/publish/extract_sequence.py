import os
import shutil
import tempfile

import pyblish.api
from avalon.tvpaint import lib


class ExtractSequence(pyblish.api.Extractor):
    label = "Extract Sequence"
    hosts = ["tvpaint"]
    families = ["review", "renderPass", "renderLayer"]

    save_mode_to_ext = {
        "avi": ".avi",
        "bmp": ".bmp",
        "cin": ".cin",
        "deep": ".dip",
        "dps": ".dps",
        "dpx": ".dpx",
        "flc": ".fli",
        "gif": ".gif",
        "ilbm": ".iff",
        "jpg": ".jpg",
        "jpeg": ".jpg",
        "pcx": ".pcx",
        "png": ".png",
        "psd": ".psd",
        "qt": ".qt",
        "rtv": ".rtv",
        "sun": ".ras",
        "tiff": ".tiff",
        "tga": ".tga",
        "vpb": ".vpb"
    }
    sequential_save_mode = {
        "bmp",
        "dpx",
        "ilbm",
        "jpg",
        "jpeg",
        "png",
        "sun",
        "tiff",
        "tga"
    }

    def process(self, instance):
        self.log.info(
            "* Processing instance \"{}\"".format(instance.data["label"])
        )

        # Get all layers and filter out not visible
        layers = instance.data["layers"]
        filtered_layers = [
            layer
            for layer in layers
            if layer["visible"]
        ]
        layer_names = [str(layer["name"]) for layer in filtered_layers]
        if not layer_names:
            self.log.info(
                f"None of the layers from the instance"
                " are visible. Extraction skipped."
            )
            return

        joined_layer_names = ", ".join(
            ["\"{}\"".format(name) for name in layer_names]
        )
        self.log.debug(
            "Instance has {} layers with names: {}".format(
                len(layer_names), joined_layer_names
            )
        )

        family_lowered = instance.data["family"].lower()
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        filename_template = self._get_filename_template(frame_end)
        ext = os.path.splitext(filename_template)[1].replace(".", "")

        self.log.debug("Using file template \"{}\"".format(filename_template))

        # Save to staging dir
        output_dir = instance.data.get("stagingDir")
        if not output_dir:
            # Create temp folder if staging dir is not set
            output_dir = tempfile.mkdtemp().replace("\\", "/")
            instance.data["stagingDir"] = output_dir

        self.log.debug(
            "Files will be rendered to folder: {}".format(output_dir)
        )

        thumbnail_filename = "thumbnail"

        # Render output
        output_files_by_frame = self.render(
            save_mode, filename_template, output_dir,
            filtered_layers, frame_start, frame_end, thumbnail_filename
        )
        thumbnail_fullpath = output_files_by_frame.pop(
            thumbnail_filename, None
        )

        # Fill gaps in sequence
        self.fill_missing_frames(
            output_files_by_frame,
            frame_start,
            frame_end,
            filename_template
        )

        # Fill tags and new families
        tags = []
        if family_lowered in ("review", "renderlayer"):
            tags.append("review")

        repre_files = [
            os.path.basename(filepath)
            for filepath in output_files_by_frame.values()
        ]
        # Sequence of one frame
        if len(repre_files) == 1:
            repre_files = repre_files[0]

        new_repre = {
            "name": ext,
            "ext": ext,
            "files": repre_files,
            "stagingDir": output_dir,
            "frameStart": frame_start + 1,
            "frameEnd": frame_end + 1,
            "tags": tags
        }
        self.log.debug("Creating new representation: {}".format(new_repre))

        instance.data["representations"].append(new_repre)

        if family_lowered in ("renderpass", "renderlayer"):
            # Change family to render
            instance.data["family"] = "render"

        if not thumbnail_fullpath:
            return

        thumbnail_ext = os.path.splitext(
            thumbnail_fullpath
        )[1].replace(".", "")
        # Create thumbnail representation
        thumbnail_repre = {
            "name": "thumbnail",
            "ext": thumbnail_ext,
            "outputName": "thumb",
            "files": os.path.basename(thumbnail_fullpath),
            "stagingDir": output_dir,
            "tags": ["thumbnail"]
        }
        instance.data["representations"].append(thumbnail_repre)

    def _get_save_mode_type(self, save_mode):
        """Extract type of save mode.

        Helps to define output files extension.
        """
        save_mode_type = (
            save_mode.lower()
            .split(" ")[0]
            .replace("\"", "")
        )
        self.log.debug("Save mode type is \"{}\"".format(save_mode_type))
        return save_mode_type

    def _get_filename_template(self, frame_end):
        """Get filetemplate for rendered files.

        This is simple template contains `{frame}{ext}` for sequential outputs
        and `single_file{ext}` for single file output. Output is rendered to
        temporary folder so filename should not matter as integrator change
        them.
        """
        frame_padding = 4
        frame_end_str_len = len(str(frame_end))
        if frame_end_str_len > frame_padding:
            frame_padding = frame_end_str_len

        return "{{:0>{}}}".format(frame_padding) + ".png"

    def render(
        self, save_mode, filename_template, output_dir, layers,
        first_frame, last_frame, thumbnail_filename
    ):
        """ Export images from TVPaint.

        Args:
            save_mode (str): Argument for `tv_savemode` george script function.
                More about save mode in documentation.
            filename_template (str): Filename template of an output. Template
                should already contain extension. Template may contain only
                keyword argument `{frame}` or index argument (for same value).
                Extension in template must match `save_mode`.
            layers (list): List of layers to be exported.
            first_frame (int): Starting frame from which export will begin.
            last_frame (int): On which frame export will end.

        Retruns:
            dict: Mapping frame to output filepath.
        """

        # Add save mode arguments to function
        save_mode = "tv_SaveMode {}".format(save_mode)

        # Map layers by position
        layers_by_position = {
            layer["position"]: layer
            for layer in layers
        }

        # Sort layer positions in reverse order
        sorted_positions = list(reversed(sorted(layers_by_position.keys())))
        if not sorted_positions:
            return

        # Create temporary layer
        new_layer_id = lib.execute_george("tv_layercreate _tmp_layer")

        # Merge layers to temp layer
        george_script_lines = []
        # Set duplicated layer as current
        george_script_lines.append("tv_layerset {}".format(new_layer_id))
        for position in sorted_positions:
            layer = layers_by_position[position]
            george_script_lines.append(
                "tv_layermerge {}".format(layer["layer_id"])
            )

        lib.execute_george_through_file("\n".join(george_script_lines))

        # Frames with keyframe
        exposure_frames = lib.get_exposure_frames(
            new_layer_id, first_frame, last_frame
        )

        # TODO what if there is not exposue frames?
        # - this force to have first frame all the time
        if first_frame not in exposure_frames:
            exposure_frames.insert(0, first_frame)

        # Restart george script lines
        george_script_lines = []
        george_script_lines.append(save_mode)

        all_output_files = {}
        for frame in exposure_frames:
            filename = filename_template.format(frame, frame=frame)
            dst_path = "/".join([output_dir, filename])
            all_output_files[frame] = os.path.normpath(dst_path)

            # Go to frame
            george_script_lines.append("tv_layerImage {}".format(frame))
            # Store image to output
            george_script_lines.append("tv_saveimage \"{}\"".format(dst_path))

        # Export thumbnail
        if thumbnail_filename:
            basename, ext = os.path.splitext(thumbnail_filename)
            if not ext:
                ext = ".jpg"
            thumbnail_fullpath = "/".join([output_dir, basename + ext])
            all_output_files[thumbnail_filename] = thumbnail_fullpath
            # Force save mode to png for thumbnail
            george_script_lines.append("tv_SaveMode \"JPG\"")
            # Go to frame
            george_script_lines.append("tv_layerImage {}".format(first_frame))
            # Store image to output
            george_script_lines.append(
                "tv_saveimage \"{}\"".format(thumbnail_fullpath)
            )

        # Delete temporary layer
        george_script_lines.append("tv_layerkill {}".format(new_layer_id))

        lib.execute_george_through_file("\n".join(george_script_lines))

        return all_output_files

    def fill_missing_frames(
        self, filepaths_by_frame, first_frame, last_frame, filename_template
    ):
        """Fill not rendered frames with previous frame.

        Extractor is rendering only frames with keyframes (exposure frames) to
        get output faster which means there may be gaps between frames.
        This function fill the missing frames.
        """
        output_dir = None
        previous_frame_filepath = None
        for frame in range(first_frame, last_frame + 1):
            if frame in filepaths_by_frame:
                previous_frame_filepath = filepaths_by_frame[frame]
                continue

            elif previous_frame_filepath is None:
                self.log.warning(
                    "No frames to fill. Seems like nothing was exported."
                )
                break

            if output_dir is None:
                output_dir = os.path.dirname(previous_frame_filepath)

            filename = filename_template.format(frame=frame)
            space_filepath = os.path.normpath(
                os.path.join(output_dir, filename)
            )
            filepaths_by_frame[frame] = space_filepath
            shutil.copy(previous_frame_filepath, space_filepath)
