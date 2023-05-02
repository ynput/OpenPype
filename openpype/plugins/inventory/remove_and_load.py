from openpype.pipeline import InventoryAction
from openpype.pipeline.legacy_io import Session
from openpype.pipeline.load.plugins import discover_loader_plugins
from openpype.pipeline.load.utils import (
    get_loader_identifier,
    remove_container,
    load_container,
)
from openpype.client import get_representation_by_id


class RemoveAndLoad(InventoryAction):
    """Delete inventory item and reload it."""

    label = "Remove and load"
    icon = "refresh"

    def process(self, containers):
        for container in containers:
            project_name = Session.get("AVALON_PROJECT")

            # Get loader
            loader_name = container["loader"]
            for plugin in discover_loader_plugins(project_name=project_name):
                if get_loader_identifier(plugin) == loader_name:
                    loader = plugin
                    break

            assert (
                loader,
                "Failed to get loader, can't remove and load container",
            )

            # Get representation
            representation = get_representation_by_id(
                project_name, container["representation"]
            )
            assert representation, "Represenatation not found"

            # Remove container
            remove_container(container)

            # Load container
            load_container(loader, representation)
