import weakref
import logging
import inspect
import avalon.api
import pyblish.api
from openpype.api import (
    get_system_settings,
    get_project_settings
)
from openpype.pipeline import (
    OpenPypePyblishPluginMixin
)
from openpype.pipeline.create import (
    BaseCreator,
    CreateContext
)


class PublisherController:
    def __init__(self, dbcon=None, headless=False):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()
        self.headless = headless

        self.create_context = CreateContext(
            self.host, dbcon, headless=False, reset=False
        )

        self._instances_refresh_callback_refs = set()
        self._plugins_refresh_callback_refs = set()

        self._resetting_plugins = False
        self._resetting_instances = False

    @property
    def dbcon(self):
        return self.create_context.dbcon

    @property
    def instances(self):
        return self.create_context.instances

    @property
    def creators(self):
        return self.create_context.creators

    @property
    def publish_plugins(self):
        return self.create_context.publish_plugins

    @property
    def plugins_with_defs(self):
        return self.create_context.plugins_with_defs

    def add_instances_refresh_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._instances_refresh_callback_refs.add(ref)

    def add_plugins_refresh_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._plugins_refresh_callback_refs.add(ref)

    def _trigger_callbacks(self, callbacks, *args, **kwargs):
        # Trigger reset callbacks
        to_remove = set()
        for ref in callbacks:
            callback = ref()
            if callback:
                callback()
            else:
                to_remove.add(ref)

        for ref in to_remove:
            callbacks.remove(ref)

    def reset(self):
        self._reset_plugin()
        self._reset_instances()

    def _reset_plugin(self):
        """Reset to initial state."""
        if self._resetting_plugins:
            return

        self._resetting_plugins = True

        self.create_context.reset_plugins()

        self._resetting_plugins = False

        self._trigger_callbacks(self._plugins_refresh_callback_refs)

    def _reset_instances(self):
        if self._resetting_instances:
            return

        self._resetting_instances = True

        self.create_context.reset_instances()

        self._resetting_instances = False

        self._trigger_callbacks(self._instances_refresh_callback_refs)

    def get_family_attribute_definitions(self, instances):
        output = []
        _attr_defs = {}
        for instance in instances:
            for attr_def in instance.family_attribute_defs:
                found_idx = None
                for idx, _attr_def in _attr_defs.items():
                    if attr_def == _attr_def:
                        found_idx = idx
                        break

                value = instance.data["family_attributes"][attr_def.key]
                if found_idx is None:
                    idx = len(output)
                    output.append((attr_def, [instance], [value]))
                    _attr_defs[idx] = attr_def
                else:
                    item = output[found_idx]
                    item[1].append(instance)
                    item[2].append(value)
        return output

    def get_publish_attribute_definitions(self, instances):
        all_defs_by_plugin_name = {}
        all_plugin_values = {}
        for instance in instances:
            for plugin_name, attr_val in instance.publish_attributes.items():
                attr_defs = attr_val.attr_defs
                if not attr_defs:
                    continue

                if plugin_name not in all_defs_by_plugin_name:
                    all_defs_by_plugin_name[plugin_name] = attr_val.attr_defs

                if plugin_name not in all_plugin_values:
                    all_plugin_values[plugin_name] = {}

                plugin_values = all_plugin_values[plugin_name]

                for attr_def in attr_defs:
                    if attr_def.key not in plugin_values:
                        plugin_values[attr_def.key] = []
                    attr_values = plugin_values[attr_def.key]

                    value = attr_val[attr_def.key]
                    attr_values.append((instance, value))

        output = []
        for plugin in self.plugins_with_defs:
            plugin_name = plugin.__name__
            if plugin_name not in all_defs_by_plugin_name:
                continue
            output.append((
                plugin_name,
                all_defs_by_plugin_name[plugin_name],
                all_plugin_values
            ))
        return output

    def create(self, family, subset_name, instance_data, options):
        # QUESTION Force to return instances or call `list_instances` on each
        #   creation? (`list_instances` may slow down...)
        creator = self.creators[family]
        creator.create(subset_name, instance_data, options)

        self._reset_instances()

    def save_instance_changes(self):
        update_list = []
        for instance in self.instances:
            instance_changes = instance.changes()
            if instance_changes:
                update_list.append((instance, instance_changes))

        if update_list:
            self.host.update_instances(update_list)

    def remove_instances(self, instances):
        self.host.remove_instances(instances)

        self._reset_instances()
