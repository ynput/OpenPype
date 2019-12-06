import os
import pyblish.api
from avalon.nuke import lib as anlib
from pype.nuke import lib as pnlib
import pype
reload(pnlib)


class ExtractReviewLutData(pype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.005
    label = "Extract Review Data Lut"

    families = ["review"]
    hosts = ["nuke"]

    def process(self, instance):
        self.log.debug(
            "_ representations: {}".format(instance.data["representations"]))

        self.log.info("Creating staging dir...")

        stagingDir = instance.data[
            'representations'][0]["stagingDir"].replace("\\", "/")
        instance.data["stagingDir"] = stagingDir

        instance.data['representations'][0]["tags"] = ["review"]

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        with anlib.maintained_selection():
            exporter = pnlib.Exporter_review_lut(
                self, instance
                    )
            data = exporter.generate_lut()

            # assign to representations
            instance.data["lutPath"] = os.path.join(
                exporter.stagingDir, exporter.file).replace("\\", "/")
            instance.data["representations"] += data["representations"]

        self.log.debug(
            "_ lutPath: {}".format(instance.data["lutPath"]))
        self.log.debug(
            "_ representations: {}".format(instance.data["representations"]))
