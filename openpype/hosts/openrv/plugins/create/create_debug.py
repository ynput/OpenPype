from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline.create import (
    LegacyCreator
)


class CreateDebugLogs(LegacyCreator):
    """Creates a quick debuger for avalon asset"""

    label = "Show Debug info in the Log"
    family = "*"
    icon = "gears"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateDebugLogs, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

    def process(self):
        """Creator main entry point.

        Args:
            instance

        """
        asset_doc = get_current_project_asset()
        asset_data = asset_doc["data"]

        print("Asset doc")
        print(asset_doc)
        print(type(asset_doc))
        print("Asset_data")
        print(type(asset_data))
        for d in asset_data:
            print(d, asset_data[d])

        print(self.name)
        print("-----done ")


