import re
from collections import defaultdict

import maya.cmds as cmds

import pyblish.api
import colorbleed.api


def get_gpu_cache_subnodes(cache):
    """Return the amount of subnodes in the cache

    This uses `maya.cmds.gpuCache(showStats=True)` and parses
    the resulting stats for the amount of internal sub nodes.

    Args:
        cache (str): gpuCache node name.

    Returns:
        int: Amount of subnodes in loaded gpuCache

    Raises:
        TypeError: when `cache` is not a gpuCache object type.
        RuntimeError: when `maya.cmds.gpuCache(showStats=True)`
            does not return stats from which we can parse the
            amount of subnodes.
    """

    # Ensure gpuCache
    if not cmds.objectType(cache, isType="gpuCache"):
        raise TypeError("Node is not a gpuCache: {0}".format(cache))

    stats = cmds.gpuCache(cache, query=True, showStats=True)
    for line in stats.splitlines():
        match = re.search('nb of internal sub nodes: ([0-9]+)$', line)
        if match:
            return int(match.group(1))

    raise RuntimeError("Couldn't parse amount of subnodes "
                       "in cache stats: {0}".format(cache))


def get_empty_gpu_caches(caches):
    empty = list()

    # Group caches per path (optimization) so
    # we check each file only once
    caches_per_path = defaultdict(list)
    for cache in caches:
        path = cmds.getAttr(cache + ".cacheFileName")
        caches_per_path[path].append(cache)

    # We consider the cache empty if its stats
    # result in 0 subnodes
    for path, path_caches in caches_per_path.items():

        cache = path_caches[0]
        num = get_gpu_cache_subnodes(cache)
        if num == 0:
            empty.extend(path_caches)

    return empty


class ValidateGPUCacheNotEmpty(pyblish.api.InstancePlugin):
    """Validates that gpuCaches have at least one visible shape in them.

    This is tested using the `maya.cmds.gpuCache(cache, showStats=True)` 
    command.
    """

    order = colorbleed.api.ValidateContentsOrder
    label = 'GpuCache has subnodes'
    families = ['colorbleed.layout']
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        caches = cmds.ls(instance, type="gpuCache", long=True)
        invalid = get_empty_gpu_caches(caches)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid nodes found: {0}".format(invalid))
