from openpype.pipeline import InventoryAction
from openpype.hosts.houdini.api.lib import (
    get_camera_from_container,
    set_camera_resolution
)

class SetAssetResolution(InventoryAction):

    label = "Set Asset Resolution"
    icon = "desktop"
    color = "orange"

    @staticmethod
    def is_compatible(container):
        print(container)
        return (
            container.get("loader") == "CameraLoader"
        )

    def process(self, containers):
        for container in containers:
            node = container["node"]
            camera = get_camera_from_container(node)
            set_camera_resolution(camera)
