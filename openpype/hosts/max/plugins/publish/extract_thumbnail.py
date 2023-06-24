import os
import tempfile
import pyblish.api
from pymxs import runtime as rt
from openpype.pipeline import publish
from openpype.hosts.max.api.lib import viewport_camera


class ExtractThumbnail(publish.Extractor):
    """
    Extract Thumbnail for Review
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Thumbnail"
    hosts = ["max"]
    families = ["review"]

    def process(self, instance):
        # TODO: Create temp directory for thumbnail
        # - this is to avoid "override" of source file
        tmp_staging = tempfile.mkdtemp(prefix="pyblish_tmp_")
        self.log.debug(
            f"Create temp directory {tmp_staging} for thumbnail"
        )
        fps = int(instance.data["fps"])
        frame = int(instance.data["frameStart"])
        instance.context.data["cleanupFullPaths"].append(tmp_staging)
        filename = "{name}_thumbnail..jpg".format(**instance.data)
        filepath = os.path.join(tmp_staging, filename)
        filepath = filepath.replace("\\", "/")
        thumbnail = self.get_filename(instance.name, frame)

        self.log.debug(
            "Writing Thumbnail to"
            " '%s' to '%s'" % (filename, tmp_staging))
        review_camera = instance.data["review_camera"]
        with viewport_camera(review_camera):
            preview_arg = self.set_preview_arg(
                instance, filepath, fps, frame)
            rt.execute(preview_arg)

        representation = {
            "name": "thumbnail",
            "ext": "png",
            "files": thumbnail,
            "stagingDir": tmp_staging,
            "thumbnail": True
        }

        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)

    def get_filename(self, filename, target_frame):
        thumbnail_name = "{}_thumbnail.{:04}.png".format(
            filename, target_frame
        )
        return thumbnail_name

    def set_preview_arg(self, instance, filepath, fps, frame):
        job_args = list()
        default_option = f'CreatePreview filename:"{filepath}"'
        job_args.append(default_option)
        frame_option = f"outputAVI:false start:{frame} end:{frame} fps:{fps}" # noqa
        job_args.append(frame_option)
        rndLevel = instance.data.get("rndLevel")
        if rndLevel:
            option = f"rndLevel:#{rndLevel}"
            job_args.append(option)
        options = [
            "percentSize", "dspGeometry", "dspShapes",
            "dspLights", "dspCameras", "dspHelpers", "dspParticles",
            "dspBones", "dspBkg", "dspGrid", "dspSafeFrame", "dspFrameNums"
        ]

        for key in options:
            enabled = instance.data.get(key)
            if enabled:
                job_args.append(f"{key}:{enabled}")
        job_str = " ".join(job_args)
        self.log.debug(job_str)

        return job_str
