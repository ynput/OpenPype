import os
import re
import tempfile
import subprocess
import pyblish.api
import pype.api
import pype.lib


class ExtractThumbnailSP(pyblish.api.InstancePlugin):
    """Extract jpeg thumbnail from component input from standalone publisher

    Uses jpeg file from component if possible (when single or multiple jpegs
    are loaded to component selected as thumbnail) otherwise extracts from
    input file/s single jpeg to temp.
    """

    label = "Extract Thumbnail SP"
    hosts = ["standalonepublisher"]
    order = pyblish.api.ExtractorOrder

    alpha_exts = ["exr", "png", "dpx"]
    color_regex = re.compile(r"^#[a-fA-F0-9]{6}$")

    # Presetable attribute
    use_bg_color = True
    ffmpeg_args = None

    def process(self, instance):
        repres = instance.data.get('representations')
        if not repres:
            return

        thumbnail_repre = None
        for repre in repres:
            if repre.get("thumbnail"):
                thumbnail_repre = repre
                break

        if not thumbnail_repre:
            return

        files = thumbnail_repre.get("files")
        if not files:
            return

        if isinstance(files, list):
            files_len = len(files)
            file = str(files[0])
        else:
            files_len = 1
            file = files

        staging_dir = None
        is_jpeg = False
        if file.endswith(".jpeg") or file.endswith(".jpg"):
            is_jpeg = True

        if is_jpeg and files_len == 1:
            # skip if already is single jpeg file
            return

        elif is_jpeg:
            # use first frame as thumbnail if is sequence of jpegs
            full_thumbnail_path = os.path.join(
                thumbnail_repre["stagingDir"], file
                )
            self.log.info(
                "For thumbnail is used file: {}".format(full_thumbnail_path)
            )

        else:
            # Convert to jpeg if not yet
            full_input_path = os.path.join(thumbnail_repre["stagingDir"], file)
            full_input_path = '"{}"'.format(full_input_path)
            self.log.info("input {}".format(full_input_path))

            full_thumbnail_path = tempfile.mkstemp(suffix=".jpg")[1]
            self.log.info("output {}".format(full_thumbnail_path))

            ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

            ffmpeg_args = self.ffmpeg_args or {}

            jpeg_items = []
            jpeg_items.append("\"{}\"".format(ffmpeg_path))
            # override file if already exists
            jpeg_items.append("-y")
            # add input filters from peresets
            jpeg_items.extend(ffmpeg_args.get("input") or [])
            # input file
            jpeg_items.append("-i {}".format(full_input_path))
            # extract only single file
            jpeg_items.append("-vframes 1")

            # output arguments from presets
            output_args = self._prepare_output_args(
                ffmpeg_args.get("output"), full_input_path, instance
            )
            if output_args:
                jpeg_items.extend(output_args)

            # output file
            jpeg_items.append(full_thumbnail_path)

            subprocess_jpeg = " ".join(jpeg_items)

            # run subprocess
            self.log.debug("Executing: {}".format(subprocess_jpeg))
            subprocess.Popen(
                subprocess_jpeg,
                stdout=subprocess.PIPE,
                shell=True
            )

        # remove thumbnail key from origin repre
        thumbnail_repre.pop("thumbnail")

        filename = os.path.basename(full_thumbnail_path)
        staging_dir = staging_dir or os.path.dirname(full_thumbnail_path)

        # create new thumbnail representation
        representation = {
            'name': 'jpg',
            'ext': 'jpg',
            'files': filename,
            "stagingDir": staging_dir,
            "tags": ["thumbnail"],
        }

        # # add Delete tag when temp file was rendered
        if not is_jpeg:
            representation["tags"].append("delete")

        self.log.info(f"New representation {representation}")
        instance.data["representations"].append(representation)

    def _prepare_output_args(self, output_args, full_input_path, instance):
        output_args = output_args or []
        ext = os.path.splitext(full_input_path)[1].replace(".", "")
        bg_color = (
            instance.context.data["presets"]
            .get("tools", {})
            .get("extract_colors", {})
            .get("bg_color")
        )
        if (
            not bg_color
            or ext not in self.alpha_exts
            or not self.use_bg_color
        ):
            return output_args

        if not self.color_regex.match(bg_color):
            self.log.warning((
                "Background color set in presets \"{}\" has invalid format."
            ).format(bg_color))
            return output_args

        video_args_dentifiers = ["-vf", "-filter:v"]
        video_filters = []
        for idx, arg in reversed(tuple(enumerate(output_args))):
            for identifier in video_args_dentifiers:
                if identifier in arg:
                    output_args.pop(idx)
                    arg = arg.replace(identifier, "").strip()
                    video_filters.append(arg)

        video_filters.extend([
            "split=2[bg][fg]",
            "[bg]drawbox=c={}:replace=1:t=fill[bg]".format(bg_color),
            "[bg][fg]overlay=format=auto"
        ])

        output_args.append(
            "-filter:v {}".format(",".join(video_filters))
        )
        return output_args
