import os
import pyblish.api
from pymxs import runtime as rt
from openpype.pipeline import publish
from openpype.hosts.max.api.lib import viewport_camera, get_max_version


class ExtractReviewAnimation(publish.Extractor):
    """
    Extract Review by Review Animation
    """

    order = pyblish.api.ExtractorOrder + 0.001
    label = "Extract Review Animation"
    hosts = ["max"]
    families = ["review"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        ext = instance.data.get("imageFormat")
        filename = "{0}..{1}".format(instance.name, ext)
        start = int(instance.data["frameStart"])
        end = int(instance.data["frameEnd"])
        fps = int(instance.data["fps"])
        filepath = os.path.join(staging_dir, filename)
        filepath = filepath.replace("\\", "/")
        filenames = self.get_files(
            instance.name, start, end, ext)

        self.log.debug(
            "Writing Review Animation to"
            " '%s' to '%s'" % (filename, staging_dir))

        review_camera = instance.data["review_camera"]
        with viewport_camera(review_camera):
            preview_arg = self.set_preview_arg(
                instance, filepath, start, end, fps)
            rt.execute(preview_arg)

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        self.log.debug("Performing Extraction ...")

        representation = {
            "name": instance.data["imageFormat"],
            "ext": instance.data["imageFormat"],
            "files": filenames,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "tags": tags,
            "preview": True,
            "camera_name": review_camera
        }
        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)

    def get_files(self, filename, start, end, ext):
        file_list = []
        for frame in range(int(start), int(end) + 1):
            actual_name = "{}.{:04}.{}".format(
                filename, frame, ext)
            file_list.append(actual_name)

        return file_list

    def set_preview_arg(self, instance, filepath,
                        start, end, fps):
        job_args = list()
        default_option = f'CreatePreview filename:"{filepath}"'
        job_args.append(default_option)
        frame_option = f"outputAVI:false start:{start} end:{end} fps:{fps}" # noqa
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

        if get_max_version() == 2024:
            # hardcoded for current stage
            auto_play_option = "autoPlay:false"
            job_args.append(auto_play_option)

        job_str = " ".join(job_args)
        self.log.debug(job_str)

        return job_str
