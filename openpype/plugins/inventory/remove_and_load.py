from openpype.pipeline import InventoryAction
from openpype.pipeline import get_current_project_name
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
        project_name = get_current_project_name()
        loaders_by_name = {
            get_loader_identifier(plugin): plugin
            for plugin in discover_loader_plugins(project_name=project_name)
        }
        for container in containers:
            # Get loader
            loader_name = container["loader"]
            loader = loaders_by_name.get(loader_name, None)
            if not loader:
                raise RuntimeError(
                    "Failed to get loader '{}', can't remove "
                    "and load container".format(loader_name)
                )

            # Get representation
            representation = get_representation_by_id(
                project_name, container["representation"]
            )
            if not representation:
                self.log.warning(
                    "Skipping remove and load because representation id is not"
                    " found in database: '{}'".format(
                        container["representation"]
                    )
                )
                continue

            # Remove container
            remove_container(container)

            # Load container
            load_container(loader, representation)
