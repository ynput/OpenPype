import os
import pyblish.api
import openpype
from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import maintained_selection


class ExtractReviewDataLut(openpype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.005
    label = "Extract Review Data Lut"

    families = ["review"]
    hosts = ["nuke"]

    def process(self, instance):
        families = instance.data["families"]
        self.log.info("Creating staging dir...")
        if "representations" in instance.data:
            staging_dir = instance.data[
                "representations"][0]["stagingDir"].replace("\\", "/")
            instance.data["stagingDir"] = staging_dir
            instance.data["representations"][0]["tags"] = ["review"]
        else:
            instance.data["representations"] = []
            # get output path
            render_path = instance.data['path']
            staging_dir = os.path.normpath(os.path.dirname(render_path))
            instance.data["stagingDir"] = staging_dir

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        # generate data
        with maintained_selection():
            exporter = plugin.ExporterReviewLut(
                self, instance
                )
            data = exporter.generate_lut()

            # assign to representations
            instance.data["lutPath"] = os.path.join(
                exporter.stagingDir, exporter.file).replace("\\", "/")
            instance.data["representations"] += data["representations"]

        if "render.farm" in families:
            instance.data["families"].remove("review")

        self.log.debug(
            "_ lutPath: {}".format(instance.data["lutPath"]))
        self.log.debug(
            "_ representations: {}".format(instance.data["representations"]))
