import uuid

from openpype.pipeline import registered_host
from openpype.tools.workfile_template_build import (
    WorkfileBuildPlaceholderDialog,
)
from openpype.pipeline.workfile.workfile_template_builder import (
    AbstractTemplateBuilder,
    PlaceholderPlugin,
    LoadPlaceholderItem,
    PlaceholderLoadMixin,
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
                LoadPlaceholderItem(item["uuid"],
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
        item_id = stub.add_placeholder(name, 1920, 1060, 25, 10)

        if not item_id:
            raise ValueError("Couldn't create a placeholder")

        container_data = {
            "id": "openpype.placeholder",
            "name": name,
            "is_placeholder": True,
            "plugin_identifier": self.identifier,
            "uuid": str(uuid.uuid4()),  # scene_identifier
            "data": placeholder_data,
            "members": [item_id]
        }

        stub.imprint(item_id, container_data)

    def populate_placeholder(self, placeholder):
        self.populate_load_placeholder(placeholder)
        errors = placeholder.get_errors()
        if errors:
            get_stub().print_msg("\n".join(errors))
        else:
            stub = get_stub()
            if not placeholder.data["keep_placeholder"]:
                metadata = stub.get_metadata()
                for item in metadata:
                    scene_identifier = item.get("uuid")
                    if (scene_identifier and
                            scene_identifier == placeholder.scene_identifier):
                        stub.delete_item(item["members"][0])
                stub.remove_instance(placeholder.scene_identifier, metadata)

    def update_placeholder(self, placeholder_item, placeholder_data):
        stub = get_stub()
        placeholder_uuid = placeholder_item.scene_identifier
        item_id = None
        for metadata_item in stub.get_metadata():
            if placeholder_uuid in metadata_item.get("uuid"):
                item_id = metadata_item["members"][0]
                break
        if not item_id:
            stub.print_msg(f"Cannot find item for {placeholder_uuid}")
            return
        metadata_item["data"] = placeholder_data
        stub.imprint(item_id, metadata_item)

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

    stub = get_stub()
    selected_items = stub.get_selected_items(False, False, True)

    if len(selected_items) != 1:
        stub.print_msg("Please select just 1 placeholder")
        return

    selected_id = selected_items[0].id
    placeholder_item = None

    placeholder_items_by_id = {
        placeholder_item.scene_identifier: placeholder_item
        for placeholder_item in builder.get_placeholders()
    }
    for metadata_item in stub.get_metadata():
        if selected_id in metadata_item.get("members"):
            placeholder_item = placeholder_items_by_id.get(
                metadata_item["uuid"])
            break

    if not placeholder_item:
        stub.print_msg("Didn't find placeholder metadata. "
                       "Remove and re-create placeholder.")
        return

    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.set_update_mode(placeholder_item)
    window.exec_()
