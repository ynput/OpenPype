import os
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt


class ExtractReviewAnimation(publish.Extractor):
    """
    Extract Review by Review Animation
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Review Animation"
    hosts = ["max"]
    families = ["review"]

    def process(self, instance):
        self.log.info("Extracting Review Animation ...")
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

        self.log.info(
            "Writing Review Animation to"
            " '%s' to '%s'" % (filename, staging_dir))

        preview_arg = self.set_preview_arg(
            instance, filepath, start, end, fps)
        rt.execute(preview_arg)

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        self.log.info("Performing Extraction ...")

        representation = {
            "name": instance.data["imageFormat"],
            "ext": instance.data["imageFormat"],
            "files": filenames,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "tags": tags,
            "preview": True,
            "camera_name": instance.data["review_camera"]
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
        percentSize = instance.data.get("percentSize")
        if percentSize:
            size = int(percentSize)
            option = f"percentSize:{size}"
            job_args.append(option)
        dspGeometry = instance.data.get("dspGeometry")
        if dspGeometry:
            option = f"dspGeometry:{dspGeometry}"
            job_args.append(option)
        dspShapes = instance.data.get("dspShapes")
        if dspShapes:
            option = f"dspShapes:{dspShapes}"
            job_args.append(option)
        dspLights = instance.data.get("dspLights")
        if dspLights:
            option = f"dspShapes:{dspLights}"
            job_args.append(option)
        dspCameras = instance.data.get("dspCameras")
        if dspCameras:
            option = f"dspCameras:{dspCameras}"
            job_args.append(option)
        dspHelpers = instance.data.get("dspHelpers")
        if dspHelpers:
            option = f"dspHelpers:{dspHelpers}"
            job_args.append(option)
        dspParticles = instance.data.get("dspParticles")
        if dspParticles:
            option = f"dspParticles:{dspParticles}"
            job_args.append(option)
        dspBones = instance.data.get("dspBones")
        if dspBones:
            option = f"dspBones:{dspBones}"
            job_args.append(option)
        dspBkg = instance.data.get("dspBkg")
        if dspBkg:
            option = f"dspBkg:{dspBkg}"
            job_args.append(option)
        dspGrid = instance.data.get("dspGrid")
        if dspGrid:
            option = f"dspBkg:{dspBkg}"
            job_args.append(option)
        dspSafeFrame = instance.data.get("dspSafeFrame")
        if dspSafeFrame:
            option = f"dspSafeFrame:{dspSafeFrame}"
            job_args.append(option)
        dspFrameNums = instance.data.get("dspFrameNums")
        if dspFrameNums:
            option = f"dspFrameNums:{dspFrameNums}"
            job_args.append(option)

        job_str = " ".join(job_args)
        self.log.info(f"{job_str}")

        return job_str
