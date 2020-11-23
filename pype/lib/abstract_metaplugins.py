from abc import ABCMeta
from pyblish.plugin import MetaPlugin, ExplicitMetaPlugin


class AbstractMetaInstancePlugin(ABCMeta, MetaPlugin):
    pass


class AbstractMetaContextPlugin(ABCMeta, ExplicitMetaPlugin):
    pass
