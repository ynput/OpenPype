import os
import logging

from openpype.pipeline.plugin_discover import (
    discover,
    register_plugin,
    register_plugin_path,
    deregister_plugin,
    deregister_plugin_path
)
from .utils import get_representation_path_from_context


class BuilderAction(list):
    families = []
    representations = []
    extensions = {"*"}
    order = 0
    is_multiple_contexts_compatible = False
    enabled = True

    options = []

    log = logging.getLogger("BuilderAction")
    log.propagate = True

    def __init__(self, context, name=None, namespace=None, options=None):
        self.fname = self.filepath_from_context(context)

    def __repr__(self):
        return "<ActionPlugin name={}>".format(self.name)

    @classmethod
    def filepath_from_context(cls, context):
        return get_representation_path_from_context(context)

    def load(self, context, name=None, namespace=None, options=None):
        """Load asset via database
        Arguments:
            context (dict): Full parenthood of representation to load
            name (str, optional): Use pre-defined name
            namespace (str, optional): Use pre-defined namespace
            options (dict, optional): Additional settings dictionary
        """
        raise NotImplementedError("Loader.load() must be "
                                  "implemented by subclass")


def discover_builder_plugins():
    plugins = discover(BuilderAction)
    return plugins


def register_builder_action(plugin):
    register_plugin(BuilderAction, plugin)


def deregister_builder_action(plugin):
    deregister_plugin(BuilderAction, plugin)


def register_builder_action_path(path):
    register_plugin_path(BuilderAction, path)


def deregister_builder_action_path(path):
    deregister_plugin_path(BuilderAction, path)
