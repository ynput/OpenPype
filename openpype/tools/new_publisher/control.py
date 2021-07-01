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

        self.creators = {}
        self.publish_plugins = []
        self.instances = []

        self._in_reset = False

    def add_reset_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._reset_callback_refs.add(ref)

    def reset(self):
        if self._in_reset:
            return

        self._in_reset = True
        self._reset()

        # Trigger reset callbacks
        to_remove = set()
        for ref in self._reset_callback_refs:
            callback = ref()
            if callback:
                callback()
            else:
                to_remove.add(ref)
        for ref in to_remove:
            self._reset_callback_refs.remove(ref)

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
            if creator is not None:
                instance_data = creator.convert_family_attribute_values(
                    instance_data
                )
            instance = AvalonInstance.from_existing(instance_data)
            instances.append(instance)

        self.instances = instances
