import pyblish.api

from openpype.lib import EnumDef

from openpype.pipeline import OpenPypePyblishPluginMixin

from openpype.pipeline.context_tools import get_current_project_asset

from openpype.hosts.fusion.api.lib import get_comp_render_range


class CollectFrameRange(
    pyblish.api.ContextPlugin,
    OpenPypePyblishPluginMixin,
):
    """Validate if the comp has the correct frame range"""

    # Move the collector so it runs before Collect Instance Data
    order = pyblish.api.CollectorOrder - 0.001

    label = "Collect Comp Frame Range"
    hosts = ["fusion"]
    frame_range_type = "asset_render"

    def process(self, context):
        # Get attributes
        attributeValues = self.get_attr_values_from_data(context.data)
        if attributeValues.get("frame_range_type") == "asset_render":
            asset_doc = get_current_project_asset()
            asset_start = asset_doc["data"]["frameStart"]
            asset_end = asset_doc["data"]["frameEnd"]
            asset_handle_start = asset_doc["data"]["handleStart"]
            asset_handle_end = asset_doc["data"]["handleEnd"]

            # Convert any potential none type to zero
            asset_handle_start = asset_handle_start or 0
            asset_handle_end = asset_handle_end or 0

            # Calcualte in/out points
            asset_global_start = asset_start - asset_handle_start
            asset_global_end = asset_end + asset_handle_end

            # If the validation is off, set the frameStart/EndHandle to the
            # current frame range, so that's what will be rendered later on
            context.data["frameStart"] = int(asset_start)
            context.data["frameEnd"] = int(asset_end)
            context.data["frameStartHandle"] = int(asset_global_start)
            context.data["frameEndHandle"] = int(asset_global_end)
            context.data["handleStart"] = int(asset_handle_start)
            context.data["handleEnd"] = int(asset_handle_end)
            context.data["frame_range_type"] = "asset_render"
        else:
            # Get the comps range
            comp = context.data["currentComp"]
            (
                comp_start,
                comp_end,
                comp_global_start,
                comp_global_end,
            ) = get_comp_render_range(comp)

            context.data["frameStart"] = int(comp_start)
            context.data["frameEnd"] = int(comp_end)
            context.data["frameStartHandle"] = int(comp_start)
            context.data["frameEndHandle"] = int(comp_end)
            context.data["handleStart"] = 0
            context.data["handleEnd"] = 0
            context.data["frame_range_type"] = "freerange_render"

        self.log.info(
            'Setting "frame_range_type" to "{}"'.format(
                context.data["frame_range_type"]
            )
        )

    @classmethod
    def get_attribute_defs(self):
        frame_ranges = {
            "asset_render": "Asset's frame range",
            "freerange_render": "Fusion's current frame range",
        }

        return [
            EnumDef(
                "frame_range_type",
                items=frame_ranges,
                default=("asset_render" in self.frame_range_type),
                label="Frame range",
                tooltip=(
                    '"Asset\'s frame range" uses the frame range'
                    " set to your opened asset."
                    '\n"Fusion\'s current frame range" will render'
                    " out the frame range you"
                    " manually have selected."
                    " The handles will both be set to 0"
                ),
            )
        ]
