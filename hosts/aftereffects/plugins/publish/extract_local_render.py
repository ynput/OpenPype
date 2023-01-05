import os
import sys
import six

import openpype.api
from openpype.hosts.aftereffects.api import get_stub


class ExtractLocalRender(openpype.api.Extractor):
    """Render RenderQueue locally."""

    order = openpype.api.Extractor.order - 0.47
    label = "Extract Local Render"
    hosts = ["aftereffects"]
    families = ["renderLocal", "render.local"]

    def process(self, instance):
        stub = get_stub()
        staging_dir = instance.data["stagingDir"]
        self.log.info("staging_dir::{}".format(staging_dir))

        # pull file name from Render Queue Output module
        render_q = stub.get_render_info()
        stub.render(staging_dir)
        if not render_q:
            raise ValueError("No file extension set in Render Queue")
        _, ext = os.path.splitext(os.path.basename(render_q.file_name))
        ext = ext[1:]

        first_file_path = None
        files = []
        self.log.info("files::{}".format(os.listdir(staging_dir)))
        for file_name in os.listdir(staging_dir):
            files.append(file_name)
            if first_file_path is None:
                first_file_path = os.path.join(staging_dir,
                                               file_name)

        resulting_files = files
        if len(files) == 1:
            resulting_files = files[0]

        repre_data = {
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "name": ext,
            "ext": ext,
            "files": resulting_files,
            "stagingDir": staging_dir
        }
        if instance.data["review"]:
            repre_data["tags"] = ["review"]

        instance.data["representations"] = [repre_data]

        ffmpeg_path = openpype.lib.get_ffmpeg_tool_path("ffmpeg")
        # Generate thumbnail.
        thumbnail_path = os.path.join(staging_dir, "thumbnail.jpg")

        args = [
            ffmpeg_path, "-y",
            "-i", first_file_path,
            "-vf", "scale=300:-1",
            "-vframes", "1",
            thumbnail_path
        ]
        self.log.debug("Thumbnail args:: {}".format(args))
        try:
            output = openpype.lib.run_subprocess(args)
        except TypeError:
            self.log.warning("Error in creating thumbnail")
            six.reraise(*sys.exc_info())

        instance.data["representations"].append({
            "name": "thumbnail",
            "ext": "jpg",
            "files": os.path.basename(thumbnail_path),
            "stagingDir": staging_dir,
            "tags": ["thumbnail"]
        })
