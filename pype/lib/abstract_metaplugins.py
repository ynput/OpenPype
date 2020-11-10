from abc import ABCMeta
from pyblish.api import InstancePlugin, ContextPlugin


class AbstractMetaInstancePlugin(ABCMeta, InstancePlugin):
    pass


class AbstractMetaContextPlugin(ABCMeta, ContextPlugin):
    pass
