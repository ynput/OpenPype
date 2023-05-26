import os
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

    def process(self, instance):
        self.log.info("Extracting Thumbnail ...")
        staging_dir = self.staging_dir(instance)
        filename = "{name}..jpg".format(**instance.data)
        filepath = os.path.join(staging_dir, filename)
        filepath = filepath.replace("\\", "/")
        thumbnail = self.get_filename(instance.name)

        self.log.info(
            "Writing Thumbnail to"
            " '%s' to '%s'" % (filename, staging_dir))

        preview_arg = self.set_preview_arg(
            instance, filepath)
        rt.execute(preview_arg)

        representation = {
            "name": "thumbnail",
            "ext": "jpg",
            "files": thumbnail,
            "stagingDir": staging_dir,
            "thumbnail": True
        }

        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)

    def get_filename(self, filename):
        return f"{filename}.0001.jpg"

    def set_preview_arg(self, instance, filepath):
        job_args = list()
        default_option = f'CreatePreview filename:"{filepath}"'
        job_args.append(default_option)

        frame_option = f"outputAVI:false start:1 end:1" # noqa
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
