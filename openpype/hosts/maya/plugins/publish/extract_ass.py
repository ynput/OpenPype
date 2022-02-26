import os

import openpype.api

from maya import cmds
from openpype.hosts.maya.api.lib import maintained_selection


class ExtractAssStandin(openpype.api.Extractor):
    """Extract the content of the instance to a ass file

    Things to pay attention to:
        - If animation is toggled, are the frames correct
        -
    """

    label = "Ass Standin (.ass)"
    hosts = ["maya"]
    families = ["ass"]
    asciiAss = False

    def process(self, instance):

        sequence = instance.data.get("exportSequence", False)

        staging_dir = self.staging_dir(instance)
        filename = "{}.ass".format(instance.name)
        filenames = list()
        file_path = os.path.join(staging_dir, filename)

        # Write out .ass file
        self.log.info("Writing: '%s'" % file_path)
        with maintained_selection():
            self.log.info("Writing: {}".format(instance.data["setMembers"]))
            cmds.select(instance.data["setMembers"], noExpand=True)

            if sequence:
                self.log.info("Extracting ass sequence")

                # Collect the start and end including handles
                start = instance.data.get("frameStartHandle", 1)
                end = instance.data.get("frameEndHandle", 1)
                step = instance.data.get("step", 0)

                exported_files = cmds.arnoldExportAss(filename=file_path,
                                                      selected=True,
                                                      asciiAss=self.asciiAss,
                                                      shadowLinks=True,
                                                      lightLinks=True,
                                                      boundingBox=True,
                                                      startFrame=start,
                                                      endFrame=end,
                                                      frameStep=step
                                                      )
                for file in exported_files:
                    filenames.append(os.path.split(file)[1])
                self.log.info("Exported: {}".format(filenames))
            else:
                self.log.info("Extracting ass")
                cmds.arnoldExportAss(filename=file_path,
                                     selected=True,
                                     asciiAss=False,
                                     shadowLinks=True,
                                     lightLinks=True,
                                     boundingBox=True
                                     )
                self.log.info("Extracted {}".format(filename))
                filenames = filename
                optionals = [
                    "frameStart", "frameEnd", "step", "handles",
                    "handleEnd", "handleStart"
                ]
                for key in optionals:
                    instance.data.pop(key, None)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'ass',
            'ext': 'ass',
            'files': filenames,
            "stagingDir": staging_dir
        }

        if sequence:
            representation['frameStart'] = start

        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))
