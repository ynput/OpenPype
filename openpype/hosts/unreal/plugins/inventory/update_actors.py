from openpype.pipeline import InventoryAction
from openpype.hosts.unreal.api.pipeline import send_request


class UpdateAllActors(InventoryAction):
    """Update all the Actors in the current level to the version of the asset
    selected in the scene manager.
    """

    label = "Replace all Actors in level to this version"
    icon = "arrow-up"

    def process(self, containers):
        send_request(
            "update_assets", params={
                "containers": containers,
                "selected": False})


class UpdateSelectedActors(InventoryAction):
    """Update only the selected Actors in the current level to the version
    of the asset selected in the scene manager.
    """

    label = "Replace selected Actors in level to this version"
    icon = "arrow-up"

    def process(self, containers):
        send_request(
            "update_assets", params={
                "containers": containers,
                "selected": True})
