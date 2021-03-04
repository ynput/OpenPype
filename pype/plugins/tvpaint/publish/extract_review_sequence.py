import os
import tempfile

import pyblish.api
from avalon.tvpaint import lib
from PIL import Image


class ExtractReviewSequence(pyblish.api.Extractor):
    label = "Extract Review Sequence"
    hosts = ["tvpaint"]
    families = ["review"]

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
        filtered_layer_ids = [
            layer["layer_id"]
            for layer in filtered_layers
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

        first_frame_filename = filename_template.format(frame_start)
        first_frame_filepath = os.path.join(output_dir, first_frame_filename)

        # Store layers visibility
        layer_visibility_by_id = {}
        for layer in instance.context.data["layersData"]:
            layer_id = layer["layer_id"]
            layer_visibility_by_id[layer_id] = layer["visible"]

        george_script_lines = []
        for layer_id in layer_visibility_by_id.keys():
            visible = layer_id in filtered_layer_ids
            value = "on" if visible else "off"
            george_script_lines.append(
                "tv_layerdisplay {} \"{}\"".format(layer_id, value)
            )
        lib.execute_george_through_file("\n".join(george_script_lines))

        # Render output
        repre_files = self.render(
            filename_template,
            output_dir,
            frame_start,
            frame_end
        )

        # Restore visibility
        george_script_lines = []
        for layer_id, visible in layer_visibility_by_id.items():
            value = "on" if visible else "off"
            george_script_lines.append(
                "tv_layerdisplay {} \"{}\"".format(layer_id, value)
            )
        lib.execute_george_through_file("\n".join(george_script_lines))

        thumbnail_filepath = os.path.join(output_dir, "thumbnail.jpg")
        if os.path.exists(first_frame_filepath):
            source_img = Image.open(first_frame_filepath)
            thumbnail_obj = Image.new("RGB", source_img.size, (255, 255, 255))
            thumbnail_obj.paste(source_img)
            thumbnail_obj.save(thumbnail_filepath)

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

        if not os.path.exists(thumbnail_filepath):
            return

        thumbnail_ext = os.path.splitext(
            thumbnail_filepath
        )[1].replace(".", "")
        # Create thumbnail representation
        thumbnail_repre = {
            "name": "thumbnail",
            "ext": thumbnail_ext,
            "outputName": "thumb",
            "files": os.path.basename(thumbnail_filepath),
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

        return "{{:0>{}}}".format(frame_padding) + ".png"

    def render(self, filename_template, output_dir, frame_start, frame_end):
        """ Export images from TVPaint.

        Args:
            filename_template (str): Filename template of an output. Template
                should already contain extension. Template may contain only
                keyword argument `{frame}` or index argument (for same value).
                Extension in template must match `save_mode`.
            output_dir (list): List of layers to be exported.
            frame_start (int): Starting frame from which export will begin.
            frame_end (int): On which frame export will end.

        Retruns:
            dict: Mapping frame to output filepath.
        """
        self.log.debug("Preparing data for rendering.")
        first_frame_filepath = os.path.join(
            output_dir,
            filename_template.format(frame_start, frame=frame_start)
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
        for frame in range(frame_start, frame_end + 1):
            output.append(
                filename_template.format(frame, frame=frame)
            )
        return output
