import os

from maya import cmds

import avalon.maya
import openpype.api
from openpype.hosts.maya.api.lib import extract_alembic


class ExtractXgenCache(openpype.api.Extractor):
    """Produce an alembic of just xgen interactive groom

    """

    label = "Extract Xgen Cache"
    hosts = ["maya"]
    families = ["xgen"]

    def process(self, instance):

        # Collect the out set nodes
        out_descriptions = [node for node in instance if cmds.nodeType(node) == "xgmSplineDescription"]

        self.log.info(out_descriptions)

        out_description = out_descriptions[0]
        self.log.info(out_description)

        # Include all descendants
        # nodes = roots + cmds.listRelatives(roots,
        #                                    allDescendents=True,
        #                                    fullPath=True) or []

        # Collect the start and end including handles
        # start = instance.data["frameStart"]
        # end = instance.data["frameEnd"]
        start = 1
        end = 1
        # handles = instance.data.get("handles", 0) or 0
        # if handles:
        #     start -= handles
        #     end += handles

        self.log.info("Extracting Xgen Cache..")
        dirname = self.staging_dir(instance)

        parent_dir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, filename)

        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                command = ('-file ' + path + ' -df "ogawa" -fr ' + str(start) + ' ' + str(end) + ' -step 1 -mxf -wfw')
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
