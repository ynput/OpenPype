import os
import shutil
import tempfile

import pyblish.api
from avalon.tvpaint import lib
from openpype.hosts.tvpaint.api.lib import composite_images
from PIL import Image, ImageDraw


class ExtractSequence(pyblish.api.Extractor):
    label = "Extract Sequence"
    hosts = ["tvpaint"]
    families = ["review", "renderPass", "renderLayer"]

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
        mark_in = instance.context.data["sceneMarkIn"]
        mark_out = instance.context.data["sceneMarkOut"]
        # Frame start/end may be stored as float
        frame_start = int(instance.data["frameStart"])
        frame_end = int(instance.data["frameEnd"])

        # Handles are not stored per instance but on Context
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]

        # --- Fallbacks ----------------------------------------------------
        # This is required if validations of ranges are ignored.
        # - all of this code won't change processing if range to render
        #   match to range of expected output

        # Prepare output frames
        output_frame_start = frame_start - handle_start
        output_frame_end = frame_end + handle_end

        # Change output frame start to 0 if handles cause it's negative number
        if output_frame_start < 0:
            self.log.warning((
                "Frame start with handles has negative value."
                " Changed to \"0\". Frames start: {}, Handle Start: {}"
            ).format(frame_start, handle_start))
            output_frame_start = 0

        # Check Marks range and output range
        output_range = output_frame_end - output_frame_start
        marks_range = mark_out - mark_in

        # Lower Mark Out if mark range is bigger than output
        # - do not rendered not used frames
        if output_range < marks_range:
            new_mark_out = mark_out - (marks_range - output_range)
            self.log.warning((
                "Lowering render range to {} frames. Changed Mark Out {} -> {}"
            ).format(marks_range + 1, mark_out, new_mark_out))
            # Assign new mark out to variable
            mark_out = new_mark_out

        # Lower output frame end so representation has right `frameEnd` value
        elif output_range > marks_range:
            new_output_frame_end = (
                output_frame_end - (output_range - marks_range)
            )
            self.log.warning((
                "Lowering representation range to {} frames."
                " Changed frame end {} -> {}"
            ).format(output_range + 1, mark_out, new_mark_out))
            output_frame_end = new_output_frame_end

        # -------------------------------------------------------------------

        filename_template = self._get_filename_template(
            # Use the biggest number
            max(mark_out, frame_end)
        )
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

        if instance.data["family"] == "review":
            output_filenames, thumbnail_fullpath = self.render_review(
                filename_template, output_dir, mark_in, mark_out
            )
        else:
            # Render output
            output_filenames, thumbnail_fullpath = self.render(
                filename_template, output_dir,
                mark_in, mark_out,
                filtered_layers
            )

        # Sequence of one frame
        if not output_filenames:
            self.log.warning("Extractor did not create any output.")
            return

        repre_files = self._rename_output_files(
            filename_template, output_dir,
            mark_in, mark_out,
            output_frame_start, output_frame_end
        )

        # Fill tags and new families
        tags = []
        if family_lowered in ("review", "renderlayer"):
            tags.append("review")

        # Sequence of one frame
        single_file = len(repre_files) == 1
        if single_file:
            repre_files = repre_files[0]

        new_repre = {
            "name": ext,
            "ext": ext,
            "files": repre_files,
            "stagingDir": output_dir,
            "tags": tags
        }

        if not single_file:
            new_repre["frameStart"] = output_frame_start
            new_repre["frameEnd"] = output_frame_end

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

        return "{{frame:0>{}}}".format(frame_padding) + ".png"

    def _rename_output_files(
        self, filename_template, output_dir,
        mark_in, mark_out, output_frame_start, output_frame_end
    ):
        # Use differnet ranges based on Mark In and output Frame Start values
        # - this is to make sure that filename renaming won't affect files that
        #   are not renamed yet
        mark_start_is_less = bool(mark_in < output_frame_start)
        if mark_start_is_less:
            marks_range = range(mark_out, mark_in - 1, -1)
            frames_range = range(output_frame_end, output_frame_start - 1, -1)
        else:
            # This is less possible situation as frame start will be in most
            #   cases higher than Mark In.
            marks_range = range(mark_in, mark_out + 1)
            frames_range = range(output_frame_start, output_frame_end + 1)

        repre_filepaths = []
        for mark, frame in zip(marks_range, frames_range):
            new_filename = filename_template.format(frame=frame)
            new_filepath = os.path.join(output_dir, new_filename)

            repre_filepaths.append(new_filepath)

            if mark != frame:
                old_filename = filename_template.format(frame=mark)
                old_filepath = os.path.join(output_dir, old_filename)
                os.rename(old_filepath, new_filepath)

        # Reverse repre files order if output
        if mark_start_is_less:
            repre_filepaths = list(reversed(repre_filepaths))

        return [
            os.path.basename(path)
            for path in repre_filepaths
        ]

    def render_review(self, filename_template, output_dir, mark_in, mark_out):
        """ Export images from TVPaint using `tv_savesequence` command.

        Args:
            filename_template (str): Filename template of an output. Template
                should already contain extension. Template may contain only
                keyword argument `{frame}` or index argument (for same value).
                Extension in template must match `save_mode`.
            output_dir (str): Directory where files will be stored.
            mark_in (int): Starting frame index from which export will begin.
            mark_out (int): On which frame index export will end.

        Retruns:
            tuple: With 2 items first is list of filenames second is path to
                thumbnail.
        """
        self.log.debug("Preparing data for rendering.")
        first_frame_filepath = os.path.join(
            output_dir,
            filename_template.format(frame=mark_in)
        )

        george_script_lines = [
            "tv_SaveMode \"PNG\"",
            "export_path = \"{}\"".format(
                first_frame_filepath.replace("\\", "/")
            ),
            "tv_savesequence '\"'export_path'\"' {} {}".format(
                mark_in, mark_out
            )
        ]
        lib.execute_george_through_file("\n".join(george_script_lines))

        first_frame_filepath = None
        output_filenames = []
        for frame in range(mark_in, mark_out + 1):
            filename = filename_template.format(frame=frame)
            output_filenames.append(filename)

            filepath = os.path.join(output_dir, filename)
            if not os.path.exists(filepath):
                raise AssertionError(
                    "Output was not rendered. File was not found {}".format(
                        filepath
                    )
                )

            if first_frame_filepath is None:
                first_frame_filepath = filepath

        thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
        if first_frame_filepath and os.path.exists(first_frame_filepath):
            source_img = Image.open(first_frame_filepath)
            thumbnail_obj = Image.new("RGB", source_img.size, (255, 255, 255))
            thumbnail_obj.paste(source_img)
            thumbnail_obj.save(thumbnail_filepath)

        return output_filenames, thumbnail_filepath

    def render(self, filename_template, output_dir, mark_in, mark_out, layers):
        """ Export images from TVPaint.

        Args:
            filename_template (str): Filename template of an output. Template
                should already contain extension. Template may contain only
                keyword argument `{frame}` or index argument (for same value).
                Extension in template must match `save_mode`.
            output_dir (str): Directory where files will be stored.
            mark_in (int): Starting frame index from which export will begin.
            mark_out (int): On which frame index export will end.
            layers (list): List of layers to be exported.

        Retruns:
            tuple: With 2 items first is list of filenames second is path to
                thumbnail.
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
            return [], None

        self.log.debug("Collecting pre/post behavior of individual layers.")
        behavior_by_layer_id = lib.get_layers_pre_post_behavior(layer_ids)

        tmp_filename_template = "pos_{pos}." + filename_template

        files_by_position = {}
        for position in sorted_positions:
            layer = layers_by_position[position]
            behavior = behavior_by_layer_id[layer["layer_id"]]

            files_by_frames = self._render_layer(
                layer,
                tmp_filename_template,
                output_dir,
                behavior,
                mark_in,
                mark_out
            )
            if files_by_frames:
                files_by_position[position] = files_by_frames
            else:
                self.log.warning((
                    "Skipped layer \"{}\". Probably out of Mark In/Out range."
                ).format(layer["name"]))

        if not files_by_position:
            layer_names = set(layer["name"] for layer in layers)
            joined_names = ", ".join(
                ["\"{}\"".format(name) for name in layer_names]
            )
            self.log.warning(
                "Layers {} do not have content in range {} - {}".format(
                    joined_names, mark_in, mark_out
                )
            )
            return [], None

        output_filepaths = self._composite_files(
            files_by_position,
            mark_in,
            mark_out,
            filename_template,
            output_dir
        )
        self._cleanup_tmp_files(files_by_position)

        output_filenames = [
            os.path.basename(filepath)
            for filepath in output_filepaths
        ]

        thumbnail_src_filepath = None
        if output_filepaths:
            thumbnail_src_filepath = output_filepaths[0]

        thumbnail_filepath = None
        if thumbnail_src_filepath and os.path.exists(thumbnail_src_filepath):
            source_img = Image.open(thumbnail_src_filepath)
            thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
            thumbnail_obj = Image.new("RGB", source_img.size, (255, 255, 255))
            thumbnail_obj.paste(source_img)
            thumbnail_obj.save(thumbnail_filepath)

        return output_filenames, thumbnail_filepath

    def _render_layer(
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

        pre_behavior = behavior["pre"]
        post_behavior = behavior["post"]

        # Check if layer is before mark in
        if frame_end_index < mark_in_index:
            # Skip layer if post behavior is "none"
            if post_behavior == "none":
                return {}

        # Check if layer is after mark out
        elif frame_start_index > mark_out_index:
            # Skip layer if pre behavior is "none"
            if pre_behavior == "none":
                return {}

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
            filename = tmp_filename_template.format(
                pos=layer_position,
                frame=frame_idx
            )
            dst_path = "/".join([output_dir, filename])
            layer_files_by_frame[frame_idx] = os.path.normpath(dst_path)

            # Go to frame
            george_script_lines.append("tv_layerImage {}".format(frame_idx))
            # Store image to output
            george_script_lines.append("tv_saveimage \"{}\"".format(dst_path))

        self.log.debug("Rendering Exposure frames {} of layer {} ({})".format(
            str(exposure_frames), layer_id, layer["name"]
        ))
        # Let TVPaint render layer's image
        lib.execute_george_through_file("\n".join(george_script_lines))

        # Fill frames between `frame_start_index` and `frame_end_index`
        self.log.debug((
            "Filling frames between first and last frame of layer ({} - {})."
        ).format(frame_start_index + 1, frame_end_index + 1))

        _debug_filled_frames = []
        prev_filepath = None
        for frame_idx in range(frame_start_index, frame_end_index + 1):
            if frame_idx in layer_files_by_frame:
                prev_filepath = layer_files_by_frame[frame_idx]
                continue

            if prev_filepath is None:
                raise ValueError("BUG: First frame of layer was not rendered!")
            _debug_filled_frames.append(frame_idx)
            filename = tmp_filename_template.format(
                pos=layer_position,
                frame=frame_idx
            )
            new_filepath = "/".join([output_dir, filename])
            self._copy_image(prev_filepath, new_filepath)
            layer_files_by_frame[frame_idx] = new_filepath

        self.log.debug("Filled frames {}".format(str(_debug_filled_frames)))

        # Fill frames by pre/post behavior of layer
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
            self.log.debug((
                "Skipping pre-behavior."
                " All frames after Mark In are rendered."
            ))
            return

        if pre_behavior == "none":
            # Empty frames are handled during `_composite_files`
            pass

        elif pre_behavior == "hold":
            # Keep first frame for whole time
            eq_frame_filepath = layer_files_by_frame[frame_start_index]
            for frame_idx in range(mark_in_index, frame_start_index):
                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
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

                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
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

                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
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
            self.log.debug((
                "Skipping post-behavior."
                " All frames up to Mark Out are rendered."
            ))
            return

        if post_behavior == "none":
            # Empty frames are handled during `_composite_files`
            pass

        elif post_behavior == "hold":
            # Keep first frame for whole time
            eq_frame_filepath = layer_files_by_frame[frame_end_index]
            for frame_idx in range(frame_end_index + 1, mark_out_index + 1):
                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

        elif post_behavior == "loop":
            # Loop backwards from last frame of layer
            for frame_idx in range(frame_end_index + 1, mark_out_index + 1):
                eq_frame_idx = frame_idx % frame_count
                eq_frame_filepath = layer_files_by_frame[eq_frame_idx]

                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
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

                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
                new_filepath = "/".join([output_dir, filename])
                self._copy_image(eq_frame_filepath, new_filepath)
                layer_files_by_frame[frame_idx] = new_filepath

    def _composite_files(
        self, files_by_position, frame_start, frame_end,
        filename_template, output_dir
    ):
        """Composite frames when more that one layer was exported.

        This method is used when more than one layer is rendered out so and
        output should be composition of each frame of rendered layers.
        Missing frames are filled with transparent images.
        """
        self.log.debug("Preparing files for compisiting.")
        # Prepare paths to images by frames into list where are stored
        #   in order of compositing.
        images_by_frame = {}
        for frame_idx in range(frame_start, frame_end + 1):
            images_by_frame[frame_idx] = []
            for position in sorted(files_by_position.keys(), reverse=True):
                position_data = files_by_position[position]
                if frame_idx in position_data:
                    filepath = position_data[frame_idx]
                    images_by_frame[frame_idx].append(filepath)

        output_filepaths = []
        missing_frame_paths = []
        random_frame_path = None
        for frame_idx in sorted(images_by_frame.keys()):
            image_filepaths = images_by_frame[frame_idx]
            output_filename = filename_template.format(frame=frame_idx)
            output_filepath = os.path.join(output_dir, output_filename)
            output_filepaths.append(output_filepath)

            # Store information about missing frame and skip
            if not image_filepaths:
                missing_frame_paths.append(output_filepath)
                continue

            # Just rename the file if is no need of compositing
            if len(image_filepaths) == 1:
                os.rename(image_filepaths[0], output_filepath)

            # Composite images
            else:
                composite_images(image_filepaths, output_filepath)

            # Store path of random output image that will 100% exist after all
            #   multiprocessing as mockup for missing frames
            if random_frame_path is None:
                random_frame_path = output_filepath

        self.log.debug(
            "Creating transparent images for frames without render {}.".format(
                str(missing_frame_paths)
            )
        )
        # Fill the sequence with transparent frames
        transparent_filepath = None
        for filepath in missing_frame_paths:
            if transparent_filepath is None:
                img_obj = Image.open(random_frame_path)
                painter = ImageDraw.Draw(img_obj)
                painter.rectangle((0, 0, *img_obj.size), fill=(0, 0, 0, 0))
                img_obj.save(filepath)
                transparent_filepath = filepath
            else:
                self._copy_image(transparent_filepath, filepath)
        return output_filepaths

    def _cleanup_tmp_files(self, files_by_position):
        """Remove temporary files that were used for compositing."""
        for data in files_by_position.values():
            for filepath in data.values():
                if os.path.exists(filepath):
                    os.remove(filepath)

    def _copy_image(self, src_path, dst_path):
        """Create a copy of an image.

        This was added to be able easier change copy method.
        """
        # Create hardlink of image instead of copying if possible
        if hasattr(os, "link"):
            os.link(src_path, dst_path)
        else:
            shutil.copy(src_path, dst_path)
