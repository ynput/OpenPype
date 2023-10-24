import copy
import contextlib

import pyblish.api

from openpype.host import HostBase, IPublishHost
from openpype.pipeline import (
    register_host,
    registered_host,
    CreatedInstance,
    Creator
)
from openpype.pipeline.create.creator_plugins import (
    BaseCreator,
    LegacyCreator,
    SubsetConvertorPlugin,
)


@contextlib.contextmanager
def no_plugins(plugins):
    """Deregister all plug-ins of class type `plugins` during context.

    Also reverts any plugins or plugin paths registered during
    the context to be undoed after the context of those plugin types.

    """
    # TODO: It seems there is no access to the registered paths
    #  or plugins so for now I'm just hacking into it here

    from openpype.pipeline.plugin_discover import _GlobalDiscover

    context = _GlobalDiscover.get_context()

    original_registered_plugins = {}
    original_registered_plugin_paths = {}
    for plugin in plugins:
        registered_plugins = context._registered_plugins.pop(plugin, None)
        original_registered_plugins[plugin] = copy.deepcopy(registered_plugins)
        registered_plugin_paths = context._registered_plugin_paths.pop(plugin,
                                                                       None)
        original_registered_plugin_paths[plugin] = copy.deepcopy(
            registered_plugin_paths)

    try:
        yield
    finally:
        # Revert registered plugins
        for plugin_key, registered_plugins in original_registered_plugins.items():  # noqa: E501
            if plugin is None:
                context._registered_plugins.pop(plugin_key, None)
            else:
                context._registered_plugins[plugin_key] = registered_plugins

        # Revert registered plugins
        for plugin_key, registered_plugin_paths in original_registered_plugin_paths.items():  # noqa: E501
            if plugin is None:
                context._registered_plugin_paths.pop(plugin_key, None)
            else:
                context._registered_plugin_paths[
                    plugin_key] = registered_plugin_paths


@contextlib.contextmanager
def no_creator_plugins():
    """Deregister all creator plugins during context, revert afterwards"""
    with no_plugins([
        BaseCreator,
        LegacyCreator,
        SubsetConvertorPlugin
    ]):
        yield


@contextlib.contextmanager
def no_pyblish_plugins():
    """Deregister all Pyblish plugins during context, revert afterwards"""
    paths = copy.deepcopy(pyblish.api.registered_paths())
    plugins = copy.deepcopy(pyblish.api.registered_plugins())

    try:
        pyblish.api.deregister_all_paths()
        pyblish.api.deregister_all_plugins()
        yield
    finally:
        pyblish.api.deregister_all_paths()
        pyblish.api.deregister_all_plugins()
        for path in paths:
            pyblish.api.register_plugin_path(path)
        for plugin in plugins:
            pyblish.api.register_plugin(plugin)


class DummyPublishHost(HostBase, IPublishHost):
    """Dummy IPublishHost"""

    name = "dummy"

    def __init__(self):
        super(DummyPublishHost, self).__init__()
        self.context_data = {}

    def get_context_data(self):
        return self.context_data.copy()

    def update_context_data(self, data, changes):
        self.context_data = data


@contextlib.contextmanager
def host_during_context(host):
    """Set registered host during context"""
    original_host = registered_host()
    try:
        register_host(host)
        yield
    finally:
        register_host(original_host)


@contextlib.contextmanager
def test_setup():
    """Set up dummy host without any registered plugins"""
    with host_during_context(DummyPublishHost()):
        with no_creator_plugins():
            with no_pyblish_plugins():
                yield


class DummyCreator(Creator):
    """Simple Creator that just caches instances into the module globally"""
    identifier = "dummy"
    label = "Dummy"
    family = "dummy"
    description = "Dummy Creator"

    cache = {
        # instance by id
        "instances": {}
    }

    def create(self, subset_name, data, pre_create_data):
        instance = CreatedInstance(self.family, subset_name, data, self)

        self._add_instance_to_context(instance)

        # Add to cache
        DummyCreator.cache["instances"][instance.id] = instance.data_to_store()

    def collect_instances(self):
        for inst_data in DummyCreator.cache.get("instances", {}).values():
            instance = CreatedInstance.from_existing(inst_data, creator=self)
            self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            data = created_inst.data_to_store()
            DummyCreator.cache[created_inst.id] = data

    def remove_instances(self, instances):
        for instance in instances:
            DummyCreator.cache.pop(instance.id, None)
            self._remove_instance_from_context(instance)
