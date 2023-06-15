import collections

from openpype.pipeline import registered_host
from openpype.tools.workfile_template_build import (
    WorkfileBuildPlaceholderDialog,
)

from openpype.pipeline.workfile.workfile_template_builder import (
    AbstractTemplateBuilder,
    PlaceholderPlugin,
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
    node_color = 4278190335

    def _collect_scene_placeholders(self):
        # Cache placeholder data to shared data
        placeholder_nodes = self.builder.get_shared_populate_data(
            "placeholder_nodes"
        )
        if placeholder_nodes is None:
            placeholder_nodes = {}
            all_groups = collections.deque()

            for item in get_stub().get

            self.builder.set_shared_populate_data(
                "placeholder_nodes", placeholder_nodes
            )
        return placeholder_nodes

    def create_placeholder(self, placeholder_data):
        placeholder_data["plugin_identifier"] = self.identifier

        stub = get_stub()

        placeholder_id = stub.create_placeholder("PLACEHOLDER",
                                                       1920,
                                                       1060,
                                                       25,
                                                       10)

        if not placeholder_id:
            raise ValueError("Couldn't create a placeholder")

        container_data = {
            "schema": "openpype:container-2.0",
            "id": "openpype.placeholder",
            "name": "PLACEHOLDER",
            "namespace": "PLACEHOLDER",
            "is_placeholder": True,
            "members": [placeholder_id]
        }

        stub.imprint(placeholder_id, container_data)

    def update_placeholder(self, placeholder_item, placeholder_data):
        # node = nuke.toNode(placeholder_item.scene_identifier)
        # imprint(node, placeholder_data)
        pass

    def _parse_placeholder_node_data(self, node):
        placeholder_data = {}
        for key in self.get_placeholder_keys():
            knob = node.knob(key)
            value = None
            if knob is not None:
                value = knob.getValue()
            placeholder_data[key] = value
        return placeholder_data



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
    for node in nuke.selectedNodes():
        node_name = node.fullName()
        if node_name in placeholder_items_by_id:
            placeholder_items.append(placeholder_items_by_id[node_name])

    # TODO show UI at least
    if len(placeholder_items) == 0:
        raise ValueError("No node selected")

    if len(placeholder_items) > 1:
        raise ValueError("Too many selected nodes")

    placeholder_item = placeholder_items[0]
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.set_update_mode(placeholder_item)
    window.exec_()
