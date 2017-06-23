import os

from maya import cmds

import pyblish.api
import colorbleed.api

import cbra.lib
from cb.utils.python.decorators import memorize


def is_latest_version(path):
    """Return whether path is the latest version.

    Args:
        path (str): Full path to published file.

    Returns:
        bool: Whether the path belongs to the latest version.

    """

    ctx = cbra.lib.parse_context(path)
    versions = cbra.lib.list_versions(ctx)
    highest = cbra.lib.find_highest_version(versions)

    if ctx.get('version', None) != highest:
        return False
    else:
        return True


@memorize
def is_latest_version_cached(path):
    """Memorized cached wrapper to `is_latest_version`"""
    return is_latest_version(path)


class ValidateLatestVersions(pyblish.api.InstancePlugin):
    """Validates content included is using latest published versions.

    If published contents are out of date they can be easily updated to the
    latest version using the scripts > pyblish > utilities > update_xxx for
    the corresponding node type.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.layout']
    label = "Latest Versions"
    actions = [colorbleed.api.SelectInvalidAction]
    optional = True

    # (node_type, attribute) that are non-referenced to check paths for
    LOCAL_CHECKS = {
        "gpuCache": "cacheFileName",
        "VRayMesh":  "fileName2"
    }

    @classmethod
    def get_invalid(cls, instance):

        all_nodes = instance[:]
        invalid = list()

        # check non-referenced nodes
        for node_type, attr in cls.LOCAL_CHECKS.iteritems():

            nodes = cmds.ls(all_nodes, type=node_type, long=True)
            referenced = cmds.ls(nodes, referencedNodes=True, long=True)
            non_referenced = [n for n in nodes if n not in referenced]

            for node in non_referenced:

                path = cmds.getAttr("{0}.{1}".format(node, attr))
                path = os.path.normpath(path)
                if not is_latest_version_cached(path):
                    invalid.append(node)

        # reference nodes related to this isntance
        referenced = cmds.ls(all_nodes, long=True, referencedNodes=True)
        referenced_nodes = set(cmds.referenceQuery(reference, referenceNode=True)
                               for reference in referenced)

        for reference in referenced_nodes:
            path = cmds.referenceQuery(reference,
                                       filename=True,
                                       withoutCopyNumber=True)
            path = os.path.normpath(path)
            if not is_latest_version_cached(path):
                invalid.append(reference)

        return invalid

    def process(self, instance):

        # Clear cache only once per publish. So we store a value on
        # the context on the first instance so we clear only once.
        name = self.__class__.__name__
        key = "_plugin_{0}_processed".format(name)
        if not instance.context.data.get(key, False):
            is_latest_version_cached.cache.clear()
            instance.context.data[key] = True

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Used Items are not updated to latest versions:"
                               "{0}".format(invalid))