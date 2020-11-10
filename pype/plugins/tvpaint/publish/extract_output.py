import os
import shutil
import tempfile

import pyblish.api
from avalon.tvpaint import pipeline, lib


class ExtractOutput(pyblish.api.Extractor):
    label = "Extract Output"
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
        "jpeg",
        "png",
        "sun",
        "tiff",
        "tga"
    }

    default_save_mode = "\"PNG\""
    save_mode_for_family = {
        "review": "\"PNG\"",
        "renderPass": "\"PNG\"",
        "renderLayer": "\"PNG\"",
    }

    def process(self, instance):
        # Get all layers and filter out not visible
        layers = instance.data["layers"]
        filtered_layers = [
            layer
            for layer in layers
            if layer["visible"]
        ]

        family_lowered = instance.data["family"].lower()

        self._prepare_save_modes()

        save_mode = self.save_mode_for_family.get(
            family_lowered, self.default_save_mode
        )
        filename_template = self._get_filename_template(save_mode)
        ext = os.path.splitext(filename_template)[1].replace(".", "")

        self.log.debug(
            "Using save mode > {} < and file template \"{}\"".format(
                save_mode, filename_template
            )
        )

        tags = ["review"]

        # TODO: This should be already collected!!!
        first_frame = int(lib.execute_george("tv_firstimage"))
        last_frame = int(lib.execute_george("tv_lastimage"))

        # Save to temp
        output_dir = tempfile.mkdtemp().replace("\\", "/")
        self.log.debug(
            "Files will be rendered to folder: {}".format(output_dir)
        )
        output_files_by_frame = self.render(
            save_mode, filename_template, output_dir,
            filtered_layers, first_frame, last_frame
        )
        self.fill_missing_frames(
            output_files_by_frame,
            first_frame,
            last_frame,
            filename_template
        )

        representations = instance.data.get("representations") or []
        repre_files = [
            os.path.basename(filepath)
            for filepath in output_files_by_frame.values()
        ]
        new_repre = {
            "name": ext,
            "ext": ext,
            "files": repre_files,
            "stagingDir": output_dir,
            "frameStart": first_frame,
            "frameEnd": last_frame,
            "tags": tags
        }
        self.log.debug("Creating new representation: {}".format(new_repre))
        representations.append(new_repre)
        instance.data["representations"] = representations

    def _prepare_save_modes(self):
        """Lower family names in keys and skip empty values."""
        new_specifications = {}
        for key, value in self.save_mode_for_family.items():
            if value:
                new_specifications[key.lower()] = value
            else:
                self.log.warning((
                    "Save mode for family \"{}\" has empty value."
                    " The family will use default save mode: > {} <."
                ).format(key, self.default_save_mode))
        self.save_mode_for_family = new_specifications

    def _get_filename_template(self, save_mode):
        """Get filetemplate for rendered files.

        This is simple template contains `{frame}{ext}` for sequential outputs
        and `single_file{ext}` for single file output. Output is rendered to
        temporary folder so filename should not matter as integrator change
        them.
        """
        _save_mode = save_mode.lower()
        _save_mode = _save_mode.split(" ")[0]
        _save_mode = _save_mode.replace("\"", "")
        self.log.info(_save_mode)
        ext = self.save_mode_to_ext.get(_save_mode)
        if ext is None:
            raise AssertionError((
                "Couldn't find file extension for TVPaint's save mode: > {} <"
            ).format(save_mode))

        is_sequence = bool(_save_mode in self.sequential_save_mode)
        if is_sequence:
            template = "{frame}" + ext
        else:
            template = "single_file" + ext
        return template

    def render(
        self, save_mode, filename_template, output_dir, layers,
        first_frame, last_frame
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

        layers_by_position = {
            layer["position"]: layer
            for layer in layers
        }

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

        # Delete temporary layer
        george_script_lines.append("tv_layerkill {}".format(new_layer_id))

        lib.execute_george_through_file("\n".join(george_script_lines))

        return all_output_files

    def fill_missing_frames(
        self, filepaths_by_frame, first_frame, last_frame, filename_template
    ):
        output_dir = None
        previous_frame_filepath = None
        for frame in range(first_frame, last_frame + 1):
            if frame in filepaths_by_frame:
                previous_frame_filepath = filepaths_by_frame[frame]
                continue

            if output_dir is None:
                output_dir = os.path.dirname(previous_frame_filepath)

            filename = filename_template.format(frame=frame)
            space_filepath = os.path.normpath(
                os.path.join(output_dir, filename)
            )
            filepaths_by_frame[frame] = space_filepath
            shutil.copy(previous_frame_filepath, space_filepath)
