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
    AvalonInstance
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

    def _reset(self):
        """Reset to initial state."""
        publish_plugins = pyblish.api.discover()
        self.publish_plugins = publish_plugins

        project_name = self.dbcon.Session["AVALON_PROJECT"]
        system_settings = get_system_settings()
        project_settings = get_project_settings(project_name)

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

        host_instances = self.host.list_instances()
        instances = []
        for instance_data in host_instances:
            family = instance_data["family"]
            creator = creators.get(family)
            instance = AvalonInstance.from_existing(
                self.host, creator, instance_data
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
        families = set()
        for instance in instances:
            family = instance.data["family"]
            families.add(family)

        plugins_with_defs = []
        for plugin in self.publish_plugins:
            if OpenPypePyblishPluginMixin in inspect.getmro(plugin):
                plugins_with_defs.append(plugin)

        filtered_plugins = pyblish.logic.plugins_by_families(
            plugins_with_defs, families
        )
        output = []
        for plugin in filtered_plugins:
            attr_defs = plugin.get_attribute_defs()
            if attr_defs:
                output.append((plugin.__name__, attr_defs))
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
