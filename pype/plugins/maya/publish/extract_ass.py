import os

import avalon.maya
import pype.api

from maya import cmds


class ExtractAssStandin(pype.api.Extractor):
    """Extract the content of the instance to a ass file

    Things to pay attention to:
        - If animation is toggled, are the frames correct
        -
    """

    label = "Ass Standin (.ass)"
    hosts = ["maya"]
    families = ["ass"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)
        filename = "{}.ass".format(instance.name)
        file_path = os.path.join(staging_dir, filename)

        # Write out .ass file
        self.log.info("Writing: '%s'" % file_path)
        with avalon.maya.maintained_selection():
            self.log.info("Writing: {}".format(instance.data["setMembers"]))
            cmds.select(instance.data["setMembers"], noExpand=True)
            cmds.arnoldExportAss(   filename=file_path,
                                    selected=True,
                                    asciiAss=True,
                                    shadowLinks=True,
                                    lightLinks=True,
                                    boundingBox=True
                                    )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'ass',
            'ext': 'ass',
            'files': filename,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))
