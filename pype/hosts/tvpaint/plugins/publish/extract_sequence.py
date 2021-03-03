import os
import shutil
import tempfile

import pyblish.api
from avalon.tvpaint import lib
from PIL import Image


def composite_images(
    input_image_paths, output_filepath, scene_width, scene_height
):
    img_obj = None
    for image_filepath in input_image_paths:
        _img_obj = Image.open(image_filepath)
        if img_obj is None:
            img_obj = _img_obj
        else:
            img_obj.alpha_composite(_img_obj)

    if img_obj is None:
        img_obj = Image.new("RGBA", (scene_width, scene_height), (0, 0, 0, 0))
    img_obj.save(output_filepath)


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
                "None of the layers from the instance"
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
        scene_width = instance.context.data["sceneWidth"]
        scene_height = instance.context.data["sceneHeight"]

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

        thumbnail_filename = "thumbnail.jpg"

        # Render output
        output_filepaths, thumbnail_fullpath = self.render(
            filename_template, output_dir, filtered_layers,
            frame_start, frame_end, thumbnail_filename,
            scene_width, scene_height
        )

        # Fill tags and new families
        tags = []
        if family_lowered in ("review", "renderlayer"):
            tags.append("review")

        repre_files = [
            os.path.basename(filepath)
            for filepath in output_filepaths
        ]
        # Sequence of one frame
        if len(repre_files) == 1:
            repre_files = repre_files[0]

        new_repre = {
            "name": ext,
            "ext": ext,
            "files": repre_files,
            "stagingDir": output_dir,
            "frameStart": frame_start,
            "frameEnd": frame_end,
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
        self, filename_template, output_dir, layers,
        frame_start, frame_end, thumbnail_filename,
        scene_width, scene_height
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
        self.log.debug("Preparing data for rendering.")

        # Map layers by position
        layers_by_position = {}
        layer_ids = []
        for layer in layers:
            position = layer["position"]
            layers_by_position[position] = layer

            layer_ids.append(layer["layer_id"])

        # Sort layer positions in reverse order
        sorted_positions = list(reversed(sorted(layers_by_position.keys())))
        if not sorted_positions:
            return

        self.log.debug("Collecting pre/post behavior of individual layers.")
        behavior_by_layer_id = lib.get_layers_pre_post_behavior(layer_ids)

        mark_in_index = frame_start - 1
        mark_out_index = frame_end - 1

        tmp_filename_template = "pos_{}." + filename_template

        files_by_position = {}
        for position in sorted_positions:
            layer = layers_by_position[position]
            behavior = behavior_by_layer_id[layer["layer_id"]]
            files_by_frames = self.render_layer(
                layer,
                tmp_filename_template,
                output_dir,
                behavior,
                mark_in_index,
                mark_out_index
            )
            files_by_position[position] = files_by_frames

        output = self._composite_files(
            files_by_position,
            output_dir,
            mark_in_index,
            mark_out_index,
            filename_template,
            thumbnail_filename,
            scene_width,
            scene_height
        )
        self._cleanup_tmp_files(files_by_position)
        return output

    def render_layer(
        self,
        layer,
        tmp_filename_template,
        output_dir,
        behavior,
        mark_in_index,
        mark_out_index
    ):
        layer_id = layer["layer_id"]
        frame_start_index = layer["frame_start"]
        frame_end_index = layer["frame_end"]
        exposure_frames = lib.get_exposure_frames(
            layer_id, frame_start_index, frame_end_index
        )
        if frame_start_index not in exposure_frames:
            exposure_frames.append(frame_start_index)

        layer_files_by_frame = {}
        george_script_lines = [
            "tv_SaveMode \"PNG\""
        ]
        layer_position = layer["position"]

        for frame_idx in exposure_frames:
            filename = tmp_filename_template.format(layer_position, frame_idx)
            dst_path = "/".join([output_dir, filename])
            layer_files_by_frame[frame_idx] = os.path.normpath(dst_path)

            # Go to frame
            george_script_lines.append("tv_layerImage {}".format(frame_idx))
            # Store image to output
            george_script_lines.append("tv_saveimage \"{}\"".format(dst_path))

        self.log.debug("Rendering exposure frames {} of layer {}".format(
            str(exposure_frames), layer_id
        ))
        # Let TVPaint render layer's image
        lib.execute_george_through_file("\n".join(george_script_lines))

        # Fill frames between `frame_start_index` and `frame_end_index`
        self.log.debug((
            "Filling frames between first and last frame of layer ({} - {})."
        ).format(frame_start_index + 1, frame_end_index + 1))

        prev_filepath = None
        for frame_idx in range(frame_start_index, frame_end_index + 1):
            if frame_idx in layer_files_by_frame:
                prev_filepath = layer_files_by_frame[frame_idx]
                continue

            if prev_filepath is None:
                raise ValueError("BUG: First frame of layer was not rendered!")

            filename = tmp_filename_template.format(layer_position, frame_idx)
            new_filepath = "/".join([output_dir, filename])
            self._copy_image(prev_filepath, new_filepath)
            layer_files_by_frame[frame_idx] = new_filepath

        # Fill frames by pre/post behavior of layer
        pre_behavior = behavior["pre"]
        post_behavior = behavior["post"]
        self.log.debug((
            "Completing image sequence of layer by pre/post behavior."
            " PRE: {} | POST: {}"
        ).format(pre_behavior, post_behavior))

        # Pre behavior
        self._fill_frame_by_pre_behavior(
            layer,
            pre_behavior,
            mark_in_index,
            layer_files_by_frame,
            tmp_filename_template,
            output_dir
        )
        self._fill_frame_by_post_behavior(
            layer,
            post_behavior,
            mark_out_index,
            layer_files_by_frame,
            tmp_filename_template,
            output_dir
        )
        return layer_files_by_frame

    def _fill_frame_by_pre_behavior(
        self,
        layer,
        pre_behavior,
        mark_in_index,
        layer_files_by_frame,
        filename_template,
        output_dir
    ):
        layer_position = layer["position"]
        frame_start_index = layer["frame_start"]
        frame_end_index = layer["frame_end"]
        frame_count = frame_end_index - frame_start_index + 1
        if mark_in_index >= frame_start_index:
            return

        if pre_behavior == "none":
            return

        if pre_behavior == "hold":
            # Keep first frame for whole time
            eq_frame_filepath = layer_files_by_frame[frame_start_index]
            for frame_idx in range(mark_in_index, frame_start_index):
                filename = filename_template.format(layer_position, frame_idx)
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

        elif pre_behavior == "loop":
            # Loop backwards from last frame of layer
            for frame_idx in reversed(range(mark_in_index, frame_start_index)):
                eq_frame_idx_offset = (
                    (frame_end_index - frame_idx) % frame_count
                )
                eq_frame_idx = frame_end_index - eq_frame_idx_offset
                eq_frame_filepath = layer_files_by_frame[eq_frame_idx]

                filename = filename_template.format(layer_position, frame_idx)
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

        elif pre_behavior == "pingpong":
            half_seq_len = frame_count - 1
            seq_len = half_seq_len * 2
            for frame_idx in reversed(range(mark_in_index, frame_start_index)):
                eq_frame_idx_offset = (frame_start_index - frame_idx) % seq_len
                if eq_frame_idx_offset > half_seq_len:
                    eq_frame_idx_offset = (seq_len - eq_frame_idx_offset)
                eq_frame_idx = frame_start_index + eq_frame_idx_offset

                eq_frame_filepath = layer_files_by_frame[eq_frame_idx]

                filename = filename_template.format(layer_position, frame_idx)
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

    def _fill_frame_by_post_behavior(
        self,
        layer,
        post_behavior,
        mark_out_index,
        layer_files_by_frame,
        filename_template,
        output_dir
    ):
        layer_position = layer["position"]
        frame_start_index = layer["frame_start"]
        frame_end_index = layer["frame_end"]
        frame_count = frame_end_index - frame_start_index + 1
        if mark_out_index <= frame_end_index:
            return

        if post_behavior == "none":
            return

        if post_behavior == "hold":
            # Keep first frame for whole time
            eq_frame_filepath = layer_files_by_frame[frame_end_index]
            for frame_idx in range(frame_end_index + 1, mark_out_index + 1):
                filename = filename_template.format(layer_position, frame_idx)
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

        elif post_behavior == "loop":
            # Loop backwards from last frame of layer
            for frame_idx in range(frame_end_index + 1, mark_out_index + 1):
                eq_frame_idx = frame_idx % frame_count
                eq_frame_filepath = layer_files_by_frame[eq_frame_idx]

                filename = filename_template.format(layer_position, frame_idx)
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

        elif post_behavior == "pingpong":
            half_seq_len = frame_count - 1
            seq_len = half_seq_len * 2
            for frame_idx in range(frame_end_index + 1, mark_out_index + 1):
                eq_frame_idx_offset = (frame_idx - frame_end_index) % seq_len
                if eq_frame_idx_offset > half_seq_len:
                    eq_frame_idx_offset = seq_len - eq_frame_idx_offset
                eq_frame_idx = frame_end_index - eq_frame_idx_offset

                eq_frame_filepath = layer_files_by_frame[eq_frame_idx]

                filename = filename_template.format(layer_position, frame_idx)
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

    def _composite_files(
        self, files_by_position, output_dir, frame_start, frame_end,
        filename_template, thumbnail_filename, scene_width, scene_height
    ):
        # Prepare paths to images by frames into list where are stored
        #   in order of compositing.
        images_by_frame = {}
        for frame_idx in range(frame_start, frame_end + 1):
            images_by_frame[frame_idx] = []
            for position in sorted(files_by_position.keys(), reverse=True):
                position_data = files_by_position[position]
                if frame_idx in position_data:
                    images_by_frame[frame_idx].append(position_data[frame_idx])

        output_filepaths = []
        thumbnail_src_filepath = None
        for frame_idx in sorted(images_by_frame.keys()):
            image_filepaths = images_by_frame[frame_idx]
            frame = frame_idx + 1

            output_filename = filename_template.format(frame)
            output_filepath = os.path.join(output_dir, output_filename)
            output_filepaths.append(output_filepath)

            if thumbnail_filename and thumbnail_src_filepath is None:
                thumbnail_src_filepath = output_filepath

            composite_images(
                image_filepaths, output_filepath, scene_width, scene_height
            )

        thumbnail_filepath = None
        if thumbnail_src_filepath:
            source_img = Image.open(thumbnail_src_filepath)
            thumbnail_filepath = os.path.join(output_dir, thumbnail_filename)
            thumbnail_obj = Image.new("RGB", source_img.size, (255, 255, 255))
            thumbnail_obj.paste(source_img)
            thumbnail_obj.save(thumbnail_filepath)

        return output_filepaths, thumbnail_filepath

    def _cleanup_tmp_files(self, files_by_position):
        for data in files_by_position.values():
            for filepath in data.values():
                os.remove(filepath)

    def _copy_image(self, src_path, dst_path):
        # Create hardlink of image instead of copying if possible
        if hasattr(os, "link"):
            os.link(src_path, dst_path)
        else:
            shutil.copy(src_path, dst_path)
