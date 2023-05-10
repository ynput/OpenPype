from openpype.pipeline import (
    InventoryAction,
    get_representation_context
)
from openpype.hosts.maya.api.lib import (
    create_rig_animation_instance,
    get_container_members,
)


class RecreateRigAnimationInstance(InventoryAction):
    """Recreate animation publish instance for loaded rigs"""

    label = "Recreate rig animation instance"
    icon = "wrench"
    color = "#888888"

    @staticmethod
    def is_compatible(container):
        return (
            container.get("loader") == "ReferenceLoader"
            and container.get("name", "").startswith("rig")
        )

    def process(self, containers):

        for container in containers:
            # todo: delete an existing entry if it exist or skip creation

            namespace = container["namespace"]
            representation_id = container["representation"]
            context = get_representation_context(representation_id)
            nodes = get_container_members(container)

            create_rig_animation_instance(nodes, context, namespace)
