import os

from maya import cmds

import avalon.maya
import colorbleed.api
from colorbleed.maya.lib import extract_alembic


def iter_parents(node):
    n = node.count("|")
    for i in range(1, n):
        yield node.rsplit("|", i)[0]


def get_highest_in_hierarchy(nodes):
    """Return the highest in the hierachies from nodes

    This will return each highest node in separate hierarchies.
    E.g.
        get_highest_in_hierarchy(["|A|B|C", "A|B", "D|E"])
        # ["A|B", "D|E"]

    """
    # Ensure we use long names
    nodes = cmds.ls(nodes, long=True)
    lookup = set(nodes)
    highest = []
    for node in nodes:
        # If no parents are within the original list
        # then this is a highest node
        if not any(n in lookup for n in iter_parents(node)):
            highest.append(node)

    return highest


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

        attrs = instance.data.get("attr", "").split(";")
        attrs = [value for value in attrs if value.strip()]
        attrs += ["cbId"]

        attr_prefixes = instance.data.get("attrPrefix", "").split(";")
        attr_prefixes = [value for value in attr_prefixes if value.strip()]

        # Get extra export arguments
        writeColorSets = instance.data.get("writeColorSets", False)

        self.log.info("Extracting pointcache..")
        dirname = self.staging_dir(instance)

        parent_dir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, filename)

        options = {
            "step": instance.data.get("step", 1.0),
            "attr": attrs,
            "attrPrefix": attr_prefixes,
            "writeVisibility": True,
            "writeCreases": True,
            "writeColorSets": writeColorSets,
            "uvWrite": True,
            "selection": True
        }

        if not instance.data.get("includeParentHierarchy", True):
            # Set the root nodes if we don't want to include parents
            # The roots are to be considered the ones that are the actual
            # direct members of the set
            options["root"] = instance.data.get("setMembers")

        if int(cmds.about(version=True)) >= 2017:
            # Since Maya 2017 alembic supports multiple uv sets - write them.
            options["writeUVSets"] = True

        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                cmds.select(nodes, noExpand=True)
                extract_alembic(file=path,
                                startFrame=start,
                                endFrame=end,
                                **options)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted {} to {}".format(instance, dirname))
