import os
import pyblish.api
from avalon.nuke import lib as anlib
from pype.hosts.nuke import lib as pnlib
import pype


class ExtractReviewDataMov(pype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.01
    label = "Extract Review Data Mov"

    families = ["review"]
    hosts = ["nuke"]

    # presets
    viewer_lut_raw = None
    bake_colorspace_fallback = None
    bake_colorspace_main = None

    def process(self, instance):
        families = instance.data["families"]
        self.log.info("Creating staging dir...")

        if "representations" not in instance.data:
            instance.data["representations"] = list()

        staging_dir = os.path.normpath(
            os.path.dirname(instance.data['path']))

        instance.data["stagingDir"] = staging_dir

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        # generate data
        with anlib.maintained_selection():
            exporter = pnlib.ExporterReviewMov(
                self, instance)

            if "render.farm" in families:
                instance.data["families"].remove("review")
                instance.data["families"].remove("ftrack")
                data = exporter.generate_mov(farm=True)

                self.log.debug(
                    "_ data: {}".format(data))

                instance.data.update({
                    "bakeRenderPath": data.get("bakeRenderPath"),
                    "bakeScriptPath": data.get("bakeScriptPath"),
                    "bakeWriteNodeName": data.get("bakeWriteNodeName")
                })
            else:
                data = exporter.generate_mov()

            # assign to representations
            instance.data["representations"] += data["representations"]

        self.log.debug(
            "_ representations: {}".format(instance.data["representations"]))
