import os
import nuke
import pyblish.api
from avalon.nuke import lib as anlib
from pype.nuke import lib as pnlib
import pype
reload(pnlib)


class ExtractReviewDataMov(pype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.01
    label = "Extract Review Data Mov"

    families = ["review"]
    hosts = ["nuke"]

    def process(self, instance):
        families = instance.data["families"]
        self.log.info("Creating staging dir...")
        if "representations" in instance.data:
            staging_dir = instance.data[
                "representations"][0]["stagingDir"].replace("\\", "/")
            instance.data["stagingDir"] = staging_dir
            instance.data["representations"][0]["tags"] = []
        else:
            instance.data["representations"] = []
            # get output path
            render_path = instance.data['path']
            staging_dir = os.path.normpath(os.path.dirname(render_path))
            instance.data["stagingDir"] = staging_dir

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        # generate data
        with anlib.maintained_selection():
            exporter = pnlib.Exporter_review_mov(
                self, instance)

            if "render.farm" in families:
                instance.data["families"].remove("review")
                instance.data["families"].remove("ftrack")
                data = exporter.generate_mov(farm=True)
            else:
                data = exporter.generate_mov()

            # assign to representations
            instance.data["representations"] += data["representations"]

        self.log.debug(
            "_ representations: {}".format(instance.data["representations"]))
