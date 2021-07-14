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
    OpenPypePyblishPluginMixin,
    BaseCreator,
    CreatedInstance
)


class PublisherController:
    def __init__(self, dbcon=None, headless=False):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()
        self.headless = headless

        if dbcon is None:
            session = avalon.api.session_data_from_environment(True)
            dbcon = avalon.api.AvalonMongoDB(session)
        dbcon.install()
        self.dbcon = dbcon

        self._reset_callback_refs = set()
        self._on_create_callback_refs = set()

        self.creators = {}

        self.publish_plugins = []
        self.plugins_with_defs = []
        self._attr_plugins_by_family = {}

        self.instances = []

        self._in_reset = False

    def add_on_reset_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._reset_callback_refs.add(ref)

    def add_on_create_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._on_create_callback_refs.add(ref)

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
        if self._in_reset:
            return

        self._in_reset = True
        self._reset()

        # Trigger reset callbacks
        self._trigger_callbacks(self._reset_callback_refs)

        self._in_reset = False

    def _get_publish_plugins_with_attr_for_family(self, family):
        if family not in self._attr_plugins_by_family:
            filtered_plugins = pyblish.logic.plugins_by_families(
                self.plugins_with_defs, [family]
            )
            self._attr_plugins_by_family[family] = filtered_plugins

        return self._attr_plugins_by_family[family]

    def _reset(self):
        """Reset to initial state."""
        # Reset publish plugins
        self._attr_plugins_by_family = {}

        publish_plugins = pyblish.api.discover()
        self.publish_plugins = publish_plugins

        # Collect plugins that can have attribute definitions
        plugins_with_defs = []
        for plugin in publish_plugins:
            if OpenPypePyblishPluginMixin in inspect.getmro(plugin):
                plugins_with_defs.append(plugin)
        self.plugins_with_defs = plugins_with_defs

        # Prepare settings
        project_name = self.dbcon.Session["AVALON_PROJECT"]
        system_settings = get_system_settings()
        project_settings = get_project_settings(project_name)

        # Discover and prepare creators
        creators = {}
        for creator in avalon.api.discover(BaseCreator):
            if inspect.isabstract(creator):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(creator))
                )
                continue
            creators[creator.family] = creator(
                system_settings,
                project_settings,
                self.headless
            )

        self.creators = creators

        # Collect instances
        host_instances = self.host.list_instances()
        instances = []
        for instance_data in host_instances:
            family = instance_data["family"]
            # Prepare publish plugins with attribute definitions

            creator = creators.get(family)
            attr_plugins = self._get_publish_plugins_with_attr_for_family(
                family
            )
            instance = CreatedInstance.from_existing(
                instance_data, creator, self.host, attr_plugins
            )
            instances.append(instance)

        self.instances = instances

    def save_instance_changes(self):
        update_list = []
        for instance in self.instances:
            instance_changes = instance.changes()
            if instance_changes:
                update_list.append((instance, instance_changes))

        if update_list:
            self.host.update_instances(update_list)

    def get_family_attribute_definitions(self, instances):
        if len(instances) == 1:
            instance = instances[0]
            output = []
            for attr_def in instance.family_attribute_defs:
                value = instance.data["family_attributes"][attr_def.key]
                output.append((attr_def, [instance], [value]))
            return output

        # TODO mulsiselection
        return ([], [], [])

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
        result = creator.create(subset_name, instance_data, options)
        if result and not isinstance(result, (list, tuple)):
            result = [result]

        for instance in result:
            self.instances.append(instance)

        self._trigger_callbacks(self._on_create_callback_refs)

        return result
