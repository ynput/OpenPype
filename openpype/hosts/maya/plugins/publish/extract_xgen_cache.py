import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api.lib import (
    suspended_refresh,
    maintained_selection
)


class ExtractXgenCache(openpype.api.Extractor):
    """Produce an alembic of just xgen interactive groom

    """

    label = "Extract Xgen ABC Cache"
    hosts = ["maya"]
    families = ["xgen"]
    optional = True

    def process(self, instance):

        # Collect the out set nodes
        out_descriptions = [node for node in instance
                            if cmds.nodeType(node) == "xgmSplineDescription"]

        start = 1
        end = 1

        self.log.info("Extracting Xgen Cache..")
        dirname = self.staging_dir(instance)

        parent_dir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, filename)

        with suspended_refresh():
            with maintained_selection():
                command = (
                    '-file '
                    + path
                    + ' -df "ogawa" -fr '
                    + str(start)
                    + ' '
                    + str(end)
                    + ' -step 1 -mxf -wfw'
                )
                for desc in out_descriptions:
                    command += (" -obj " + desc)
                cmds.xgmSplineCache(export=True, j=command)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": dirname,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted {} to {}".format(instance, dirname))
