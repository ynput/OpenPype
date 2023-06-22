import os
import tempfile
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt


class ExtractThumbnail(publish.Extractor):
    """
    Extract Thumbnail for Review
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Thumbnail"
    hosts = ["max"]
    families = ["review"]
    start

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
        thumbnail = self.get_filename(instance.name)

        self.log.debug(
            "Writing Thumbnail to"
            " '%s' to '%s'" % (filename, tmp_staging))

        preview_arg = self.set_preview_arg(
            instance, filepath, fps, frame)
        rt.execute(preview_arg)

        representation = {
            "name": "thumbnail",
            "ext": "jpg",
            "files": thumbnail,
            "stagingDir": tmp_staging,
            "thumbnail": True
        }

        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)

    def get_filename(self, filename):
        return f"{filename}_thumbnail.0001.jpg"

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
