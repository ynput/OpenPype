import os
import re
from collections import defaultdict

import pyblish.api
import colorbleed.api

import maya.cmds as cmds


class ValidateYetiCacheUniqueFilenames(pyblish.api.InstancePlugin):
    """Validates Yeti nodes in instance have unique filename patterns.

    This is to ensure Yeti caches in a single instance don't overwrite each
    other's files when published to a single flat folder structure.

    For example:
        cache1:       path/to/arm.%04d.fur
        cache2: other/path/to/arm.%04d.fur

    Both these caches point to unique files, though they have the same filename
    pattern. When copied to a single folder they would overwrite each other,
    and as such are considered invalid. To fix this rename the caches filenames
    to be unique, like `left_arm.%04d.fur` and `right_arm.%04d.fur`.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = 'Yeti Cache Unique Filenames'
    families = ['colorbleed.furYeti']
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        members = instance.data["setMembers"]
        shapes = cmds.ls(members, dag=True, leaf=True, shapes=True, long=True)
        yeti_nodes = cmds.ls(shapes, type="pgYetiMaya", long=True)

        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes in instance.")

        def _to_pattern(path):
            """Path to pattern that pyseq.get_sequences can use"""
            return re.sub(r"([0-9]+|%[0-9]+d)(.fur)$", r"[0-9]*\2",  path)

        invalid = list()

        # Collect cache patterns
        cache_patterns = defaultdict(list)
        for node in yeti_nodes:

            path = cmds.getAttr(node + ".cacheFileName")
            if not path:
                invalid.append(node)
                cls.log.warning("Node has no cache file name set: "
                                "{0}".format(node))
                continue

            filename = os.path.basename(path)
            pattern = _to_pattern(filename)

            cache_patterns[pattern].append(node)

        # Identify non-unique cache patterns
        for pattern, nodes in cache_patterns.iteritems():
            if len(nodes) > 1:
                cls.log.warning("Nodes have same filename pattern ({0}): "
                                "{1}".format(pattern, nodes))
                invalid.extend(nodes)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("Invalid nodes: {0}".format(invalid))
            raise RuntimeError("Invalid yeti nodes in instance. "
                               "See logs for details.")
