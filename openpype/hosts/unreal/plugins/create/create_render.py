# -*- coding: utf-8 -*-
from openpype.pipeline import CreatorError
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator
)
from openpype.hosts.unreal.api.pipeline import (
    send_request
)
from openpype.lib import UILabelDef


class CreateRender(UnrealAssetCreator):
    """Create instance for sequence for rendering"""

    identifier = "io.openpype.creators.unreal.render"
    label = "Render"
    family = "render"
    icon = "eye"

    def create(self, subset_name, instance_data, pre_create_data):
        sel_objects = send_request("get_selected_assets")

        if not sel_objects:
            raise CreatorError("Please select at least one Level Sequence.")

        for selected_asset_path in sel_objects:
            master_lvl, master_seq, seq_data = send_request(
                "create_render", params={"sequence_path": selected_asset_path})

            # If we didn't find the selected asset, we don't create the
            # instance.
            if not seq_data:
                send_request(
                    "log",
                    params={
                        "message": f"Skipping {selected_asset_path}."
                                   "It isn't a sub-sequence of the master "
                                   "sequence.",
                        "level": "warning"
                    })
                continue

            instance_data["members"] = [selected_asset_path]
            instance_data["sequence"] = selected_asset_path
            instance_data["master_sequence"] = master_seq
            instance_data["master_level"] = master_lvl
            instance_data["output"] = seq_data.get('output')
            instance_data["frameStart"] = seq_data.get('frame_range')[0]
            instance_data["frameEnd"] = seq_data.get('frame_range')[1]

            super(CreateRender, self).create(
                subset_name,
                instance_data,
                pre_create_data)

    def get_pre_create_attr_defs(self):
        return [
            UILabelDef("Select the sequence to render.")
        ]
