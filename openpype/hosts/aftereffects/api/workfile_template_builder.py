import collections
import uuid

from openpype.pipeline import registered_host
from openpype.tools.workfile_template_build import (
    WorkfileBuildPlaceholderDialog,
)
from openpype.pipeline.workfile.workfile_template_builder import (
    AbstractTemplateBuilder,
    PlaceholderPlugin,
    LoadPlaceholderItem,
    CreatePlaceholderItem,
    PlaceholderLoadMixin,
    PlaceholderCreateMixin
)
from openpype.hosts.aftereffects.api import get_stub

PLACEHOLDER_SET = "PLACEHOLDERS_SET"


class AETemplateBuilder(AbstractTemplateBuilder):
    """Concrete implementation of AbstractTemplateBuilder for AE"""

    def import_template(self, path):
        """Import template into current scene.
        Block if a template is already loaded.

        Args:
            path (str): A path to current template (usually given by
            get_template_preset implementation)

        Returns:
            bool: Whether the template was successfully imported or not
        """

        # TODO check if the template is already imported


        return True


class AEPlaceholderPlugin(PlaceholderPlugin):
    """Contains generic methods for all PlaceholderPlugins.

    Cannot inherit from `PlaceholderPlugin` as it is actually not implementing
    all methods.
    """

    def _collect_scene_placeholders(self):
        # Cache placeholder data to shared data
        # Returns list of dicts
        placeholder_items = self.builder.get_shared_populate_data(
            "placeholder_items"
        )
        if not placeholder_items:
            placeholder_items = []
            for item in get_stub().get_metadata():
                if not item.get("is_placeholder"):
                    continue
                placeholder_items.append(item)

            self.builder.set_shared_populate_data(
                "placeholder_items", placeholder_items
            )
        return placeholder_items

    def collect_placeholders(self):
        output = []
        scene_placeholders = self._collect_scene_placeholders()
        for item in scene_placeholders:
            if item.get("plugin_identifier") != self.identifier:
                continue

            output.append(
                LoadPlaceholderItem(item["scene_identifier"],
                                    item["data"],
                                    self)
            )

        return output


class AEPlaceholderLoadPlugin(AEPlaceholderPlugin, PlaceholderLoadMixin):
    identifier = "aftereffects.load"
    label = "AfterEffects load"

    def create_placeholder(self, placeholder_data):

        stub = get_stub()
        name = "LOADERPLACEHOLDER"
        placeholder_id = stub.add_placeholder(name,
                                              1920,
                                              1060,
                                              25,
                                              10)

        if not placeholder_id:
            raise ValueError("Couldn't create a placeholder")

        container_data = {
            "schema": "openpype:container-2.0",
            "id": "openpype.placeholder",
            "name": name,
            "is_placeholder": True,
            "plugin_identifier": self.identifier,
            "scene_identifier": str(uuid.uuid4()),
            "data": placeholder_data,
            "members": [placeholder_id]
        }

        stub.imprint(placeholder_id, container_data)

    def populate_placeholder(self, placeholder):
        self.populate_load_placeholder(placeholder)
        errors = placeholder.get_errors()
        if errors:
            get_stub().print_msg("\n".join(errors))

    def repopulate_placeholder(self, placeholder):
        repre_ids = self._get_loaded_repre_ids()
        self.populate_load_placeholder(placeholder, repre_ids)

    def update_placeholder(self, placeholder_item, placeholder_data):
        self.log.info("Wont implement for now")

    def get_placeholder_options(self, options=None):
        return self.get_load_plugin_options(options)


def build_workfile_template(*args, **kwargs):
    builder = AETemplateBuilder(registered_host())
    builder.build_template(*args, **kwargs)


def update_workfile_template(*args):
    builder = AETemplateBuilder(registered_host())
    builder.rebuild_template()


def create_placeholder(*args):
    host = registered_host()
    builder = AETemplateBuilder(host)
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.exec_()


def update_placeholder(*args):
    host = registered_host()
    builder = AETemplateBuilder(host)
    placeholder_items_by_id = {
        placeholder_item.scene_identifier: placeholder_item
        for placeholder_item in builder.get_placeholders()
    }
    placeholder_items = []

    # TODO show UI at least
    if len(placeholder_items) == 0:
        raise ValueError("No node selected")

    if len(placeholder_items) > 1:
        raise ValueError("Too many selected nodes")

    placeholder_item = placeholder_items[0]
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.set_update_mode(placeholder_item)
    window.exec_()