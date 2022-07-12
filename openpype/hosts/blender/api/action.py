import bpy

import pyblish.api

from openpype.pipeline import update_container, discover_inventory_actions
from openpype.pipeline.publish import get_errored_instances_from_context

from .pipeline import AVALON_PROPERTY


def _get_invalid_nodes(context, plugin):
    """Get invalid nodes from context and plugin."""
    errored_instances = get_errored_instances_from_context(context)
    instances = pyblish.api.instances_by_plugin(errored_instances, plugin)
    invalid_nodes = list()
    for instance in instances:
        invalid = plugin.get_invalid(instance)
        if isinstance(invalid, (list, tuple)):
            invalid_nodes.extend(invalid)
        else:
            invalid_nodes.append(invalid)
    return invalid_nodes


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid objects in Blender when a publish plug-in failed."""
    label = "Select Invalid"
    on = "failed"
    icon = "search"

    def process(self, context, plugin):
        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes...")
        invalid_nodes = set(_get_invalid_nodes(context, plugin))

        if not invalid_nodes:
            self.log.warning(
                "Failed plug-in doesn't have any selectable objects."
            )
            return

        # Get selectable objects from invalid nodes.
        objects = set()
        for node in invalid_nodes:
            if isinstance(node, bpy.types.Object):
                objects.add(node)
            elif isinstance(node, bpy.types.Collection):
                objects.update(node.all_objects)

        bpy.ops.object.select_all(action='DESELECT')

        invalid_names = [obj.name for obj in objects]
        self.log.info(
            "Selecting invalid objects: %s", ", ".join(invalid_names)
        )
        # Select the objects and also make the last one the active object.
        for obj in objects:
            obj.select_set(True)

        bpy.context.view_layer.objects.active = list(objects)[-1]


class UpdateContainer(pyblish.api.Action):
    """Update Container with last representation."""

    label = "Update With Last Representation"
    on = "failed"
    icon = "refresh"

    def process(self, context, plugin):
        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes...")
        update_actions = [
            (action, set())
            for action in discover_inventory_actions()
            if action.__name__.startswith("Update")
        ]
        invalid_nodes = set(_get_invalid_nodes(context, plugin))

        out_to_date_collections = set()
        for node in invalid_nodes:
            if isinstance(node, bpy.types.Collection):
                out_to_date_collections.add(node)

        for collection in out_to_date_collections:
            self.log.info(f"Updating {collection.name}..")
            container = collection.get(AVALON_PROPERTY)

            for action, containers in update_actions:
                if action.is_compatible(container):
                    containers.add(container)
                    break
            else:
                update_container(container, -1)

        for action, containers in update_actions:
            if containers:
                action().process(containers)
