import os

import maya.cmds as cmds

import pyblish.api
import colorbleed.api

import cbra.lib
from cb.utils.python.decorators import memorize


def isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


@memorize
def is_published_path(path):
    """Return whether path is from a published file"""

    # Quick check (optimization) without going through the folder
    # structure
    if cbra.lib.DIR_PUBLISH.lower() not in path.lower():
        return False

    try:
        context = cbra.lib.parse_context(path)
    except RuntimeError:
        context = dict()

    return all([context.get("family", None),
                context.get("subset", None),
                context.get("version", None)])


class ValidateLayoutNodes(pyblish.api.InstancePlugin):
    """Validates that layout nodes behave to certain rules

    Gpu caches in a layout may not have sub-frame offsets, like offsets with a
    value after the decimal point. (e.g. 1.45)

    Gpu caches loaded in a layout MUST come from a published source that has
    family and version.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = 'Layout Nodes'
    families = ['colorbleed.layout']
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        caches = cmds.ls(instance, type="gpuCache", long=True)

        # Validate sub-frame offsets
        invalid_offsets = list()
        for cache in caches:

            offset = cmds.getAttr("{}.animOffset".format(cache))
            if not isclose(offset, round(offset)):
                cls.log.warning("Invalid sub-frame offset on: %s" % cache)
                invalid_offsets.append(cache)

        # Validate gpuCache paths are from published files
        invalid_paths = list()
        for cache in caches:
            path = cmds.getAttr("{}.cacheFileName".format(cache))
            path = os.path.normpath(path)
            if not is_published_path(path):
                cls.log.warning("GpuCache path not from published file: "
                                "{0} -> {1}".format(cache, path))
                invalid_paths.append(cache)

        invalid = invalid_offsets + invalid_paths

        return invalid

    def process(self, instance):

        # Clear cache only once per publish. So we store a value on
        # the context on the first instance so we clear only once.
        name = self.__class__.__name__
        key = "_plugin_{0}_processed".format(name)
        if not instance.context.data.get(key, False):
            is_published_path.cache.clear()
            instance.context.data[key] = True

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid nodes found: {0}".format(invalid))
