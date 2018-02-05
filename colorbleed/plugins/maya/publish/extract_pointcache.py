import os

from maya import cmds

import avalon.maya
import colorbleed.api
from colorbleed.maya.lib import extract_alembic


class ExtractColorbleedAlembic(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals, uvs, creases are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Pointcache (Alembic)"
    hosts = ["maya"]
    families = ["colorbleed.pointcache",
                "colorbleed.model"]

    def process(self, instance):

        nodes = instance[:]

        # Collect the start and end including handles
        start = instance.data.get("startFrame", 1)
        end = instance.data.get("endFrame", 1)
        handles = instance.data.get("handles", 0)
        if handles:
            start -= handles
            end += handles

        # Get extra export arguments
        writeColorSets = instance.data.get("writeColorSets", False)

        self.log.info("Extracting animation..")
        dirname = self.staging_dir(instance)

        self.log.info("nodes: %s" % str(nodes))

        parent_dir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, filename)

        options = {
            "step": instance.data.get("step", 1.0),
            "attr": ["cbId"],
            "writeVisibility": True,
            "writeCreases": True,
            "writeColorSets": writeColorSets,
            "uvWrite": True,
            "selection": True
        }

        if int(cmds.about(version=True)) >= 2017:
            # Since Maya 2017 alembic supports multiple uv sets - write them.
            options["writeUVSets"] = True

        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                cmds.select(nodes, noExpand=True)
                extract_alembic(file=path,
                                startFrame=start,
                                endFrame=end,
                                **{"step": instance.data.get("step", 1.0),
                                   "attr": ["cbId"],
                                   "attrPrefix": ["vray"],
                                   "writeVisibility": True,
                                   "writeCreases": True,
                                   "writeColorSets": writeColorSets,
                                   "uvWrite": True,
                                   "selection": True})

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted {} to {}".format(instance, dirname))
