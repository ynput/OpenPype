import os

from maya import cmds

from openpype.hosts.maya.api.lib import maintained_selection
from openpype.pipeline import publish


class ExtractLight(publish.Extractor):
    """Extract as Light.

    Extracts as Maya Scene (ma).
    """

    label = "Light"
    hosts = ["maya"]
    families = ["light"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filename = "{}.ma".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # Perform extraction
        self.log.info("Performing extraction ...")
        selection = instance.data.get("setMembers", list())
        with maintained_selection():
            cmds.select(selection, noExpand=True)
            cmds.file(
                path,
                force=True,
                type="mayaAscii",
                exportSelected=True,
                preserveReferences=True,
                constructionHistory=True,
                shader=True,
                constraints=True,
                expressions=True
            )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "ma",
            "ext": "ma",
            "files": filename,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info(
            "Extracted instance '{}' to: {}".format(instance.name, path)
        )
