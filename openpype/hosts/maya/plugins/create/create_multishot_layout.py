from openpype.hosts.maya.api import plugin
from openpype.lib import BoolDef
from openpype import AYON_SERVER_ENABLED
from ayon_api import get_folder_by_name


class CreateMultishotLayout(plugin.MayaCreator):
    """A grouped package of loaded content"""

    identifier = "io.openpype.creators.maya.multishotlayout"
    label = "Multishot Layout"
    family = "layout"
    icon = "camera"

    def get_instance_attr_defs(self):

        return [
            BoolDef("groupLoadedAssets",
                    label="Group Loaded Assets",
                    tooltip="Enable this when you want to publish group of "
                            "loaded asset",
                    default=False)
        ]

    def create(self, subset_name, instance_data, pre_create_data):
        # TODO: get this needs to be switched to get_folder_by_path
        #       once the fork to pure AYON is done.
        # WARNING: this will not work for projects where the asset name
        #          is not unique across the project until the switch mentioned
        #          above is done.
        current_folder = get_folder_by_name(instance_data["asset"])


# blast this creator if Ayon server is not enabled
if not AYON_SERVER_ENABLED:
    del CreateMultishotLayout
