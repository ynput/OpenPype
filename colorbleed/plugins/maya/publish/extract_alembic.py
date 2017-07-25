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
    families = ["colorbleed.model", "colorbleed.pointcache"]
    optional = True

    def process(self, instance):

        parent_dir = self.staging_dir(instance)
        filename = "%s.abc" % instance.name
        path = os.path.join(parent_dir, filename)

        attrPrefix = instance.data.get("attrPrefix", [])
        attrPrefix.append("cb")

        options = copy.deepcopy(instance.data)
        options['attrPrefix'] = attrPrefix

        # Ensure visibility keys are written
        options['writeVisibility'] = True

        # Write creases
        options['writeCreases'] = True

        # Ensure UVs are written
        options['uvWrite'] = True

        options['selection'] = True
        options["attr"] = ["cbId"]

        # force elect items to ensure all items get exported by Alembic
        members = instance.data("setMembers")
        print "Members : {}".format(members)

        cmds.select(members)
        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                extract_alembic(file=path, **options)

        cmds.select(clear=True)
