import os
import copy

from openpype.hosts.tvpaint.worker import (
    SenderTVPaintCommands,
    ExecuteSimpleGeorgeScript,
    ExecuteGeorgeScript
)

import pyblish.api
from openpype.hosts.tvpaint.lib import (
    calculate_layers_extraction_data,
    get_frame_filename_template,
    fill_reference_frames,
    composite_rendered_layers,
    rename_filepaths_by_frame_start
)
from PIL import Image


class ExtractTVPaintSequences(pyblish.api.Extractor):
    label = "Extract TVPaint Sequences"
    hosts = ["webpublisher"]
    targets = ["tvpaint_worker"]

    # Context plugin does not have families filtering
    families_filter = ["review", "renderPass", "renderLayer"]

    job_queue_root_key = "jobs_root"

    # Modifiable with settings
    review_bg = [255, 255, 255, 255]

    def process(self, context):
        # Get workfle path
        workfile_path = context.data["workfilePath"]
        jobs_root = context.data["jobsRoot"]
        jobs_root_slashed = jobs_root.replace("\\", "/")

        # Prepare scene data
        scene_data = context.data["sceneData"]
        scene_mark_in = scene_data["sceneMarkIn"]
        scene_mark_out = scene_data["sceneMarkOut"]
        scene_start_frame = scene_data["sceneStartFrame"]
        scene_bg_color = scene_data["sceneBgColor"]

        # Prepare layers behavior
        behavior_by_layer_id = context.data["layersPrePostBehavior"]
        exposure_frames_by_layer_id = context.data["layersExposureFrames"]

        # Handles are not stored per instance but on Context
        handle_start = context.data["handleStart"]
        handle_end = context.data["handleEnd"]

        # Get JobQueue module
        modules = context.data["openPypeModules"]
        job_queue_module = modules["job_queue"]

        tvpaint_commands = SenderTVPaintCommands(
            workfile_path, job_queue_module
        )

        # Change scene Start Frame to 0 to prevent frame index issues
        #   - issue is that TVPaint versions deal with frame indexes in a
        #     different way when Start Frame is not `0`
        # NOTE It will be set back after rendering
        tvpaint_commands.add_command(
            ExecuteSimpleGeorgeScript("tv_startframe 0")
        )

        root_key_replacement = "{" + self.job_queue_root_key + "}"
        after_render_instances = []
        for instance in context:
            instance_families = set(instance.data.get("families", []))
            instance_families.add(instance.data["family"])
            valid = False
            for family in instance_families:
                if family in self.families_filter:
                    valid = True
                    break

            if not valid:
                continue

            self.log.info("* Preparing commands for instance \"{}\"".format(
                instance.data["label"]
            ))
            # Get all layers and filter out not visible
            layers = instance.data["layers"]
            filtered_layers = [layer for layer in layers if layer["visible"]]
            if not filtered_layers:
                self.log.info(
                    "None of the layers from the instance"
                    " are visible. Extraction skipped."
                )
                continue

            joined_layer_names = ", ".join([
                "\"{}\"".format(str(layer["name"]))
                for layer in filtered_layers
            ])
            self.log.debug(
                "Instance has {} layers with names: {}".format(
                    len(filtered_layers), joined_layer_names
                )
            )

            # Staging dir must be created during collection
            staging_dir = instance.data["stagingDir"].replace("\\", "/")

            job_root_template = staging_dir.replace(
                jobs_root_slashed, root_key_replacement
            )

            # Frame start/end may be stored as float
            frame_start = int(instance.data["frameStart"])
            frame_end = int(instance.data["frameEnd"])

            # Prepare output frames
            output_frame_start = frame_start - handle_start
            output_frame_end = frame_end + handle_end

            # Change output frame start to 0 if handles cause it's negative
            #   number
            if output_frame_start < 0:
                self.log.warning((
                    "Frame start with handles has negative value."
                    " Changed to \"0\". Frames start: {}, Handle Start: {}"
                ).format(frame_start, handle_start))
                output_frame_start = 0

            # Create copy of scene Mark In/Out
            mark_in, mark_out = scene_mark_in, scene_mark_out

            # Fix possible changes of output frame
            mark_out, output_frame_end = self._fix_range_changes(
                mark_in, mark_out, output_frame_start, output_frame_end
            )
            filename_template = get_frame_filename_template(
                max(scene_mark_out, output_frame_end)
            )

            # -----------------------------------------------------------------
            self.log.debug(
                "Files will be rendered to folder: {}".format(staging_dir)
            )

            output_filepaths_by_frame_idx = {}
            for frame_idx in range(mark_in, mark_out + 1):
                filename = filename_template.format(frame=frame_idx)
                filepath = os.path.join(staging_dir, filename)
                output_filepaths_by_frame_idx[frame_idx] = filepath

            # Prepare data for post render processing
            post_render_data = {
                "output_dir": staging_dir,
                "layers": filtered_layers,
                "output_filepaths_by_frame_idx": output_filepaths_by_frame_idx,
                "instance": instance,
                "is_layers_render": False,
                "output_frame_start": output_frame_start,
                "output_frame_end": output_frame_end
            }
            # Store them to list
            after_render_instances.append(post_render_data)

            # Review rendering
            if instance.data["family"] == "review":
                self.add_render_review_command(
                    tvpaint_commands, mark_in, mark_out, scene_bg_color,
                    job_root_template, filename_template
                )
                continue

            # Layers rendering
            extraction_data_by_layer_id = calculate_layers_extraction_data(
                filtered_layers,
                exposure_frames_by_layer_id,
                behavior_by_layer_id,
                mark_in,
                mark_out
            )
            filepaths_by_layer_id = self.add_render_command(
                tvpaint_commands,
                job_root_template,
                staging_dir,
                filtered_layers,
                extraction_data_by_layer_id
            )
            # Add more data to post render processing
            post_render_data.update({
                "is_layers_render": True,
                "extraction_data_by_layer_id": extraction_data_by_layer_id,
                "filepaths_by_layer_id": filepaths_by_layer_id
            })

        # Change scene frame Start back to previous value
        tvpaint_commands.add_command(
            ExecuteSimpleGeorgeScript(
                "tv_startframe {}".format(scene_start_frame)
            )
        )
        self.log.info("Sending the job and waiting for response...")
        tvpaint_commands.send_job_and_wait()
        self.log.info("Render job finished")

        for post_render_data in after_render_instances:
            self._post_render_processing(post_render_data, mark_in, mark_out)

    def _fix_range_changes(
        self, mark_in, mark_out, output_frame_start, output_frame_end
    ):
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
        return mark_out, output_frame_end

    def _post_render_processing(self, post_render_data, mark_in, mark_out):
        # Unpack values
        instance = post_render_data["instance"]
        output_filepaths_by_frame_idx = (
            post_render_data["output_filepaths_by_frame_idx"]
        )
        is_layers_render = post_render_data["is_layers_render"]
        output_dir = post_render_data["output_dir"]
        layers = post_render_data["layers"]
        output_frame_start = post_render_data["output_frame_start"]
        output_frame_end = post_render_data["output_frame_end"]

        # Trigger post processing of layers rendering
        #   - only few frames were rendered this will complete the sequence
        #   - multiple layers can be in single instance they must be composite
        #       over each other
        if is_layers_render:
            self._finish_layer_render(
                layers,
                post_render_data["extraction_data_by_layer_id"],
                post_render_data["filepaths_by_layer_id"],
                mark_in,
                mark_out,
                output_filepaths_by_frame_idx
            )

        # Create thumbnail
        thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
        thumbnail_src_path = output_filepaths_by_frame_idx[mark_in]
        self._create_thumbnail(thumbnail_src_path, thumbnail_filepath)

        # Rename filepaths to final frames
        repre_files = self._rename_output_files(
            output_filepaths_by_frame_idx,
            mark_in,
            mark_out,
            output_frame_start
        )

        # Fill tags and new families
        family_lowered = instance.data["family"].lower()
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

        thumbnail_ext = os.path.splitext(thumbnail_filepath)[1]
        # Create thumbnail representation
        thumbnail_repre = {
            "name": "thumbnail",
            "ext": thumbnail_ext.replace(".", ""),
            "outputName": "thumb",
            "files": os.path.basename(thumbnail_filepath),
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

    def add_render_review_command(
        self,
        tvpaint_commands,
        mark_in,
        mark_out,
        scene_bg_color,
        job_root_template,
        filename_template
    ):
        """ Export images from TVPaint using `tv_savesequence` command.

        Args:
            output_dir (str): Directory where files will be stored.
            mark_in (int): Starting frame index from which export will begin.
            mark_out (int): On which frame index export will end.
            scene_bg_color (list): Bg color set in scene. Result of george
                script command `tv_background`.
        """
        self.log.debug("Preparing data for rendering.")
        bg_color = self._get_review_bg_color()
        first_frame_filepath = "/".join([
            job_root_template,
            filename_template.format(frame=mark_in)
        ])

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

        tvpaint_commands.add_command(
            ExecuteGeorgeScript(
                george_script_lines,
                root_dir_key=self.job_queue_root_key
            )
        )

    def add_render_command(
        self,
        tvpaint_commands,
        job_root_template,
        staging_dir,
        layers,
        extraction_data_by_layer_id
    ):
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
        # Map layers by position
        layers_by_id = {
            layer["layer_id"]: layer
            for layer in layers
        }

        # Render layers
        filepaths_by_layer_id = {}
        for layer_id, render_data in extraction_data_by_layer_id.items():
            layer = layers_by_id[layer_id]
            frame_references = render_data["frame_references"]
            filenames_by_frame_index = render_data["filenames_by_frame_index"]

            filepaths_by_frame = {}
            command_filepath_by_frame = {}
            for frame_idx, ref_idx in frame_references.items():
                # None reference is skipped because does not have source
                if ref_idx is None:
                    filepaths_by_frame[frame_idx] = None
                    continue
                filename = filenames_by_frame_index[frame_idx]

                filepaths_by_frame[frame_idx] = os.path.join(
                    staging_dir, filename
                )
                if frame_idx == ref_idx:
                    command_filepath_by_frame[frame_idx] = "/".join(
                        [job_root_template, filename]
                    )

            self._add_render_layer_command(
                tvpaint_commands, layer, command_filepath_by_frame
            )
            filepaths_by_layer_id[layer_id] = filepaths_by_frame

        return filepaths_by_layer_id

    def _add_render_layer_command(
        self, tvpaint_commands, layer, filepaths_by_frame
    ):
        george_script_lines = [
            # Set current layer by position
            "tv_layergetid {}".format(layer["position"]),
            "layer_id = result",
            "tv_layerset layer_id",
            "tv_SaveMode \"PNG\""
        ]

        for frame_idx, filepath in filepaths_by_frame.items():
            if filepath is None:
                continue

            # Go to frame
            george_script_lines.append("tv_layerImage {}".format(frame_idx))
            # Store image to output
            george_script_lines.append(
                "tv_saveimage \"{}\"".format(filepath.replace("\\", "/"))
            )

        tvpaint_commands.add_command(
            ExecuteGeorgeScript(
                george_script_lines,
                root_dir_key=self.job_queue_root_key
            )
        )

    def _finish_layer_render(
        self,
        layers,
        extraction_data_by_layer_id,
        filepaths_by_layer_id,
        mark_in,
        mark_out,
        output_filepaths_by_frame_idx
    ):
        # Fill frames between `frame_start_index` and `frame_end_index`
        self.log.debug("Filling frames not rendered frames.")
        for layer_id, render_data in extraction_data_by_layer_id.items():
            frame_references = render_data["frame_references"]
            filepaths_by_frame = filepaths_by_layer_id[layer_id]
            fill_reference_frames(frame_references, filepaths_by_frame)

        # Prepare final filepaths where compositing should store result
        self.log.info("Started compositing of layer frames.")
        composite_rendered_layers(
            layers, filepaths_by_layer_id,
            mark_in, mark_out,
            output_filepaths_by_frame_idx
        )

    def _create_thumbnail(self, thumbnail_src_path, thumbnail_filepath):
        if not os.path.exists(thumbnail_src_path):
            return

        source_img = Image.open(thumbnail_src_path)

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

    def _get_review_bg_color(self):
        red = green = blue = 255
        if self.review_bg:
            if len(self.review_bg) == 4:
                red, green, blue, _ = self.review_bg
            elif len(self.review_bg) == 3:
                red, green, blue = self.review_bg
        return (red, green, blue)
