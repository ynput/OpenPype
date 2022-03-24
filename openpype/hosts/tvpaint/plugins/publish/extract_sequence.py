import os
import copy
import tempfile

from PIL import Image

import pyblish.api
from openpype.hosts.tvpaint.api import lib
from openpype.hosts.tvpaint.lib import (
    calculate_layers_extraction_data,
    get_frame_filename_template,
    fill_reference_frames,
    composite_rendered_layers,
    rename_filepaths_by_frame_start,
)


class ExtractSequence(pyblish.api.Extractor):
    label = "Extract Sequence"
    hosts = ["tvpaint"]
    families = ["review", "renderPass", "renderLayer"]

    # Modifiable with settings
    review_bg = [255, 255, 255, 255]

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

        # Change scene Start Frame to 0 to prevent frame index issues
        #   - issue is that TVPaint versions deal with frame indexes in a
        #     different way when Start Frame is not `0`
        # NOTE It will be set back after rendering
        scene_start_frame = instance.context.data["sceneStartFrame"]
        lib.execute_george("tv_startframe 0")

        # Frame start/end may be stored as float
        frame_start = int(instance.data["frameStart"])
        frame_end = int(instance.data["frameEnd"])

        # Handles are not stored per instance but on Context
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]

        scene_bg_color = instance.context.data["sceneBgColor"]

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
            ).format(output_range + 1, mark_out, new_output_frame_end))
            output_frame_end = new_output_frame_end

        # -------------------------------------------------------------------

        # Save to staging dir
        output_dir = instance.data.get("stagingDir")
        if not output_dir:
            # Create temp folder if staging dir is not set
            output_dir = (
                tempfile.mkdtemp(prefix="tvpaint_render_")
            ).replace("\\", "/")
            instance.data["stagingDir"] = output_dir

        self.log.debug(
            "Files will be rendered to folder: {}".format(output_dir)
        )

        if instance.data["family"] == "review":
            result = self.render_review(
                output_dir, mark_in, mark_out, scene_bg_color
            )
        else:
            # Render output
            result = self.render(
                output_dir, mark_in, mark_out, filtered_layers
            )

        output_filepaths_by_frame_idx, thumbnail_fullpath = result

        # Change scene frame Start back to previous value
        lib.execute_george("tv_startframe {}".format(scene_start_frame))

        # Sequence of one frame
        if not output_filepaths_by_frame_idx:
            self.log.warning("Extractor did not create any output.")
            return

        repre_files = self._rename_output_files(
            output_filepaths_by_frame_idx,
            mark_in,
            mark_out,
            output_frame_start
        )

        # Fill tags and new families
        tags = []
        if family_lowered in ("review", "renderlayer"):
            tags.append("review")

        # Sequence of one frame
        single_file = len(repre_files) == 1
        if single_file:
            repre_files = repre_files[0]

        # Extension is hardcoded
        #   - changing extension would require change code
        new_repre = {
            "name": "png",
            "ext": "png",
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

    def _rename_output_files(
        self, filepaths_by_frame, mark_in, mark_out, output_frame_start
    ):
        new_filepaths_by_frame = rename_filepaths_by_frame_start(
            filepaths_by_frame, mark_in, mark_out, output_frame_start
        )

        repre_filenames = []
        for filepath in new_filepaths_by_frame.values():
            repre_filenames.append(os.path.basename(filepath))

        if mark_in < output_frame_start:
            repre_filenames = list(reversed(repre_filenames))

        return repre_filenames

    def render_review(
        self, output_dir, mark_in, mark_out, scene_bg_color
    ):
        """ Export images from TVPaint using `tv_savesequence` command.

        Args:
            output_dir (str): Directory where files will be stored.
            mark_in (int): Starting frame index from which export will begin.
            mark_out (int): On which frame index export will end.
            scene_bg_color (list): Bg color set in scene. Result of george
                script command `tv_background`.

        Returns:
            tuple: With 2 items first is list of filenames second is path to
                thumbnail.
        """
        filename_template = get_frame_filename_template(mark_out)

        self.log.debug("Preparing data for rendering.")
        first_frame_filepath = os.path.join(
            output_dir,
            filename_template.format(frame=mark_in)
        )

        bg_color = self._get_review_bg_color()

        george_script_lines = [
            # Change bg color to color from settings
            "tv_background \"color\" {} {} {}".format(*bg_color),
            "tv_SaveMode \"PNG\"",
            "export_path = \"{}\"".format(
                first_frame_filepath.replace("\\", "/")
            ),
            "tv_savesequence '\"'export_path'\"' {} {}".format(
                mark_in, mark_out
            )
        ]
        if scene_bg_color:
            # Change bg color back to previous scene bg color
            _scene_bg_color = copy.deepcopy(scene_bg_color)
            bg_type = _scene_bg_color.pop(0)
            orig_color_command = [
                "tv_background",
                "\"{}\"".format(bg_type)
            ]
            orig_color_command.extend(_scene_bg_color)

            george_script_lines.append(" ".join(orig_color_command))

        lib.execute_george_through_file("\n".join(george_script_lines))

        first_frame_filepath = None
        output_filepaths_by_frame_idx = {}
        for frame_idx in range(mark_in, mark_out + 1):
            filename = filename_template.format(frame=frame_idx)
            filepath = os.path.join(output_dir, filename)

            output_filepaths_by_frame_idx[frame_idx] = filepath

            if not os.path.exists(filepath):
                raise AssertionError(
                    "Output was not rendered. File was not found {}".format(
                        filepath
                    )
                )

            if first_frame_filepath is None:
                first_frame_filepath = filepath

        thumbnail_filepath = None
        if first_frame_filepath and os.path.exists(first_frame_filepath):
            thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
            source_img = Image.open(first_frame_filepath)
            if source_img.mode.lower() != "rgb":
                source_img = source_img.convert("RGB")
            source_img.save(thumbnail_filepath)

        return output_filepaths_by_frame_idx, thumbnail_filepath

    def render(self, output_dir, mark_in, mark_out, layers):
        """ Export images from TVPaint.

        Args:
            output_dir (str): Directory where files will be stored.
            mark_in (int): Starting frame index from which export will begin.
            mark_out (int): On which frame index export will end.
            layers (list): List of layers to be exported.

        Returns:
            tuple: With 2 items first is list of filenames second is path to
                thumbnail.
        """
        self.log.debug("Preparing data for rendering.")

        # Map layers by position
        layers_by_position = {}
        layers_by_id = {}
        layer_ids = []
        for layer in layers:
            layer_id = layer["layer_id"]
            position = layer["position"]
            layers_by_position[position] = layer
            layers_by_id[layer_id] = layer

            layer_ids.append(layer_id)

        # Sort layer positions in reverse order
        sorted_positions = list(reversed(sorted(layers_by_position.keys())))
        if not sorted_positions:
            return [], None

        self.log.debug("Collecting pre/post behavior of individual layers.")
        behavior_by_layer_id = lib.get_layers_pre_post_behavior(layer_ids)
        exposure_frames_by_layer_id = lib.get_layers_exposure_frames(
            layer_ids, layers
        )
        extraction_data_by_layer_id = calculate_layers_extraction_data(
            layers,
            exposure_frames_by_layer_id,
            behavior_by_layer_id,
            mark_in,
            mark_out
        )
        # Render layers
        filepaths_by_layer_id = {}
        for layer_id, render_data in extraction_data_by_layer_id.items():
            layer = layers_by_id[layer_id]
            filepaths_by_layer_id[layer_id] = self._render_layer(
                render_data, layer, output_dir
            )

        # Prepare final filepaths where compositing should store result
        output_filepaths_by_frame = {}
        thumbnail_src_filepath = None
        finale_template = get_frame_filename_template(mark_out)
        for frame_idx in range(mark_in, mark_out + 1):
            filename = finale_template.format(frame=frame_idx)

            filepath = os.path.join(output_dir, filename)
            output_filepaths_by_frame[frame_idx] = filepath

            if thumbnail_src_filepath is None:
                thumbnail_src_filepath = filepath

        self.log.info("Started compositing of layer frames.")
        composite_rendered_layers(
            layers, filepaths_by_layer_id,
            mark_in, mark_out,
            output_filepaths_by_frame
        )

        self.log.info("Compositing finished")
        thumbnail_filepath = None
        if thumbnail_src_filepath and os.path.exists(thumbnail_src_filepath):
            source_img = Image.open(thumbnail_src_filepath)
            thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
            # Composite background only on rgba images
            # - just making sure
            if source_img.mode.lower() == "rgba":
                bg_color = self._get_review_bg_color()
                self.log.debug("Adding thumbnail background color {}.".format(
                    " ".join([str(val) for val in bg_color])
                ))
                bg_image = Image.new("RGBA", source_img.size, bg_color)
                thumbnail_obj = Image.alpha_composite(bg_image, source_img)
                thumbnail_obj.convert("RGB").save(thumbnail_filepath)

            else:
                self.log.info((
                    "Source for thumbnail has mode \"{}\" (Expected: RGBA)."
                    " Can't use thubmanail background color."
                ).format(source_img.mode))
                source_img.save(thumbnail_filepath)

        return output_filepaths_by_frame, thumbnail_filepath

    def _get_review_bg_color(self):
        red = green = blue = 255
        if self.review_bg:
            if len(self.review_bg) == 4:
                red, green, blue, _ = self.review_bg
            elif len(self.review_bg) == 3:
                red, green, blue = self.review_bg
        return (red, green, blue)

    def _render_layer(self, render_data, layer, output_dir):
        frame_references = render_data["frame_references"]
        filenames_by_frame_index = render_data["filenames_by_frame_index"]

        layer_id = layer["layer_id"]
        george_script_lines = [
            "tv_layerset {}".format(layer_id),
            "tv_SaveMode \"PNG\""
        ]

        filepaths_by_frame = {}
        frames_to_render = []
        for frame_idx, ref_idx in frame_references.items():
            # None reference is skipped because does not have source
            if ref_idx is None:
                filepaths_by_frame[frame_idx] = None
                continue
            filename = filenames_by_frame_index[frame_idx]
            dst_path = "/".join([output_dir, filename])
            filepaths_by_frame[frame_idx] = dst_path
            if frame_idx != ref_idx:
                continue

            frames_to_render.append(str(frame_idx))
            # Go to frame
            george_script_lines.append("tv_layerImage {}".format(frame_idx))
            # Store image to output
            george_script_lines.append("tv_saveimage \"{}\"".format(dst_path))

        self.log.debug("Rendering Exposure frames {} of layer {} ({})".format(
            ",".join(frames_to_render), layer_id, layer["name"]
        ))
        # Let TVPaint render layer's image
        lib.execute_george_through_file("\n".join(george_script_lines))

        # Fill frames between `frame_start_index` and `frame_end_index`
        self.log.debug("Filling frames not rendered frames.")
        fill_reference_frames(frame_references, filepaths_by_frame)

        return filepaths_by_frame
