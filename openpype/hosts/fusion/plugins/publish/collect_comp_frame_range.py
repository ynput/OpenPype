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

            # Convert any potential none type to zero
            asset_handle_start = asset_doc["data"].get("handleStart", 0)
            asset_handle_end = asset_doc["data"].get("handleEnd", 0)

            # Calcualte in/out points
            asset_global_start = asset_start - asset_handle_start
            asset_global_end = asset_end + asset_handle_end

            # If the validation is off, set the frameStart/EndHandle to the
            # current frame range, so that's what will be rendered later on
            frame_start = int(asset_start)
            frame_end = int(asset_end)
            frame_start_handle = int(asset_global_start)
            frame_end_handle = int(asset_global_end)
            handle_start = int(asset_handle_start)
            handle_end = int(asset_handle_end)
            frame_range_type = "asset_render"
        else:
            # Get the comps range
            (
                comp_start,
                comp_end,
                comp_global_start,
                comp_global_end,
            ) = get_comp_render_range(context.data["currentComp"])

            frame_start = frame_start_handle = int(comp_start)
            frame_end = frame_end_handle = int(comp_end)
            handle_start = 0
            handle_end = 0
            frame_range_type = "freerange_render"

        context.data["frameStart"] = frame_start
        context.data["frameEnd"] = frame_end
        context.data["frameStartHandle"] = frame_start_handle
        context.data["frameEndHandle"] = frame_end_handle
        context.data["handleStart"] = handle_start
        context.data["handleEnd"] = handle_end
        context.data["frame_range_type"] = frame_range_type

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
