import os
import shutil
import time
import tempfile
import multiprocessing

import pyblish.api
from avalon.tvpaint import lib
from pype.hosts.tvpaint.lib import composite_images
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

        if instance.data["family"] == "review":
            repre_files, thumbnail_fullpath = self.render_review(
                filename_template, output_dir, frame_start, frame_end
            )
        else:
            # Render output
            repre_files, thumbnail_fullpath = self.render(
                filename_template, output_dir, filtered_layers,
                frame_start, frame_end, scene_width, scene_height
            )

        # Fill tags and new families
        tags = []
        if family_lowered in ("review", "renderlayer"):
            tags.append("review")

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

    def render_review(
        self, filename_template, output_dir, frame_start, frame_end
    ):
        """ Export images from TVPaint.

        Args:
            filename_template (str): Filename template of an output. Template
                should already contain extension. Template must contain
                keyword argument `{frame}`. Extension in template must match
                `save_mode`.
            output_dir (list): List of layers to be exported.
            frame_start (int): Starting frame from which export will begin.
            frame_end (int): On which frame export will end.

        Retruns:
            dict: Mapping frame to output filepath.
        """
        self.log.debug("Preparing data for rendering.")
        first_frame_filepath = os.path.join(
            output_dir,
            filename_template.format(frame=frame_start)
        )
        mark_in = frame_start - 1
        mark_out = frame_end - 1

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

        output = []
        first_frame_filepath = None
        for frame in range(frame_start, frame_end + 1):
            filename = filename_template.format(frame=frame)
            output.append(filename)
            if first_frame_filepath is None:
                first_frame_filepath = os.path.join(output_dir, filename)

        thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
        if first_frame_filepath and os.path.exists(first_frame_filepath):
            source_img = Image.open(first_frame_filepath)
            thumbnail_obj = Image.new("RGB", source_img.size, (255, 255, 255))
            thumbnail_obj.paste(source_img)
            thumbnail_obj.save(thumbnail_filepath)
        return output, thumbnail_filepath

    def render(
        self, filename_template, output_dir, layers,
        frame_start, frame_end, scene_width, scene_height
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

        tmp_filename_template = "pos_{pos}." + filename_template

        files_by_position = {}
        is_single_layer = len(sorted_positions) == 1
        for position in sorted_positions:
            layer = layers_by_position[position]
            behavior = behavior_by_layer_id[layer["layer_id"]]

            if is_single_layer:
                _template = filename_template
            else:
                _template = tmp_filename_template

            files_by_frames = self._render_layer(
                layer,
                _template,
                output_dir,
                behavior,
                mark_in_index,
                mark_out_index
            )
            if is_single_layer:
                output_filepaths = list(files_by_frames.values())
            else:
                files_by_position[position] = files_by_frames

        if not is_single_layer:
            output_filepaths = self._composite_files(
                files_by_position,
                output_dir,
                mark_in_index,
                mark_out_index,
                filename_template,
                scene_width,
                scene_height
            )
            self._cleanup_tmp_files(files_by_position)

        thumbnail_src_filepath = None
        thumbnail_filepath = None
        if output_filepaths:
            thumbnail_src_filepath = tuple(sorted(output_filepaths))[0]

        if thumbnail_src_filepath and os.path.exists(thumbnail_src_filepath):
            source_img = Image.open(thumbnail_src_filepath)
            thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
            thumbnail_obj = Image.new("RGB", source_img.size, (255, 255, 255))
            thumbnail_obj.paste(source_img)
            thumbnail_obj.save(thumbnail_filepath)

        repre_files = [
            os.path.basename(path)
            for path in output_filepaths
        ]
        return repre_files, thumbnail_filepath

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

            filename = tmp_filename_template.format(
                pos=layer_position,
                frame=frame_idx
            )
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
            # Take size from first image and fill it with transparent color
            first_filename = filename_template.format(
                pos=layer_position,
                frame=frame_start_index
            )
            first_filepath = os.path.join(output_dir, first_filename)
            empty_image_filepath = None
            for frame_idx in reversed(range(mark_in_index, frame_start_index)):
                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
                filepath = os.path.join(output_dir, filename)
                if empty_image_filepath is None:
                    img_obj = Image.open(first_filepath)
                    painter = ImageDraw.Draw(img_obj)
                    painter.rectangle((0, 0, *img_obj.size), fill=(0, 0, 0, 0))
                    img_obj.save(filepath)
                    empty_image_filepath = filepath
                else:
                    self._copy_image(empty_image_filepath, filepath)

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
            return

        if post_behavior == "none":
            # Take size from last image and fill it with transparent color
            last_filename = filename_template.format(
                pos=layer_position,
                frame=frame_end_index
            )
            last_filepath = os.path.join(output_dir, last_filename)
            empty_image_filepath = None
            for frame_idx in range(frame_end_index + 1, mark_out_index + 1):
                filename = filename_template.format(
                    pos=layer_position,
                    frame=frame_idx
                )
                filepath = os.path.join(output_dir, filename)
                if empty_image_filepath is None:
                    img_obj = Image.open(last_filepath)
                    painter = ImageDraw.Draw(img_obj)
                    painter.rectangle((0, 0, *img_obj.size), fill=(0, 0, 0, 0))
                    img_obj.save(filepath)
                    empty_image_filepath = filepath
                else:
                    self._copy_image(empty_image_filepath, filepath)

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
        self, files_by_position, output_dir, frame_start, frame_end,
        filename_template, scene_width, scene_height
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

        process_count = os.cpu_count()
        if process_count > 1:
            process_count -= 1

        processes = {}
        output_filepaths = []
        for frame_idx in sorted(images_by_frame.keys()):
            image_filepaths = images_by_frame[frame_idx]
            frame = frame_idx + 1

            output_filename = filename_template.format(frame=frame)
            output_filepath = os.path.join(output_dir, output_filename)
            output_filepaths.append(output_filepath)

            processes[frame_idx] = multiprocessing.Process(
                target=composite_images,
                args=(
                    image_filepaths, output_filepath, scene_width, scene_height
                )
            )

        # Wait until all processes are done
        running_processes = {}
        while True:
            for idx in tuple(running_processes.keys()):
                process = running_processes[idx]
                if not process.is_alive():
                    running_processes.pop(idx).join()

            if processes and len(running_processes) != process_count:
                indexes = list(processes.keys())
                for _ in range(process_count - len(running_processes)):
                    if not indexes:
                        break
                    idx = indexes.pop(0)
                    running_processes[idx] = processes.pop(idx)
                    running_processes[idx].start()

            if not running_processes and not processes:
                break

            time.sleep(0.01)

        return output_filepaths

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
