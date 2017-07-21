import os
import copy

import maya.cmds as cmds

import avalon.maya
import colorbleed.api
from colorbleed.maya.lib import extract_alembic


class ExtractAlembic(colorbleed.api.Extractor):
    """Extract Alembic Cache

    This extracts an Alembic cache using the `-selection` flag to minimize
    the extracted content to solely what was Collected into the instance.

    """
    label = "Alembic"
    families = ["colorbleed.model",
                "colorbleed.pointcache",
                "colorbleed.proxy"]
    optional = True

    def process(self, instance):

        parent_dir = self.staging_dir(instance)
        filename = "%s.abc" % instance.name
        path = os.path.join(parent_dir, filename)

        options = copy.deepcopy(instance.data)
        options['selection'] = True
        options["attr"] = ["cbId"]

        # force elect items to ensure all items get exported by Alembic
        members = instance.data("setMembers")
        cmds.select(members)
        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                extract_alembic(file=path, **options)

        cmds.select(clear=True)
