import os

from maya import cmds

import avalon.maya
import colorbleed.api
from colorbleed.maya.lib import extract_alembic


class ExtractColorbleedAnimation(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Animation"
    hosts = ["maya"]
    families = ["colorbleed.animation"]

    def process(self, instance):

        # Collect the out set nodes
        out_sets = [node for node in instance if node.endswith("out_SET")]
        if len(out_sets) != 1:
            raise RuntimeError("Couldn't find exactly one out_SET: "
                               "{0}".format(out_sets))
        out_set = out_sets[0]
        nodes = cmds.sets(out_set, query=True)

        # Include all descendants
        nodes += cmds.listRelatives(nodes,
                                    allDescendents=True,
                                    fullPath=True) or []

        # Collect the start and end including handles
        start = instance.data["startFrame"]
        end = instance.data["endFrame"]
        handles = instance.data.get("handles", 0)
        if handles:
            start -= handles
            end += handles

        self.log.info("Extracting animation..")
        dirname = self.staging_dir(instance)

        self.log.info("nodes: %s" % str(nodes))

        parent_dir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, filename)

        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                cmds.select(nodes, noExpand=True)
                extract_alembic(file=path,
                                startFrame=start,
                                endFrame=end,
                                **{"step": instance.data.get("step", 1.0),
                                   "attr": ["cbId"],
                                   "writeVisibility": True,
                                   "writeCreases": True,
                                   "uvWrite": True,
                                   "selection": True})

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted {} to {}".format(instance, dirname))
