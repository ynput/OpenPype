import tde4

from openpype.hosts.equalizer.api import EqualizerCreator
from openpype.lib import EnumDef


class CreateMatchMove(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.matchmove"
    label = "Match Move"
    family = "matchmove"
    icon = "camera"

    def get_instance_attr_defs(self):
        camera_enum = [
            {"value": "__all__", "label": "All Cameras"},
            {"value": "__current__", "label": "Current Camera"},
            {"value": "__ref__", "label": "Reference Cameras"},
            {"value": "__seq__", "label": "Sequence Cameras"},
        ]
        camera_list = tde4.getCameraList()
        camera_enum.extend(
            {"label": tde4.getCameraName(camera), "value": camera}
            for camera in camera_list
            if tde4.getCameraEnabledFlag(camera)
        )
        # try to get list of models
        model_enum = [
            {"value": "__none__", "label": "No 3D Models At All"},
            {"value": "__all__", "label": "All 3D Models"},
        ]
        point_groups = tde4.getPGroupList()
        for point_group in point_groups:
            model_list = tde4.get3DModelList(point_group, 0)
            model_enum.extend(
                {
                    "label": tde4.get3DModelName(point_group, model),
                    "value": model
                } for model in model_list
            )
        return [
            EnumDef("camera_selection",
                    items=camera_enum,
                    default="__current__",
                    label="Camera(s) to publish",
                    tooltip="Select cameras to publish"),
            EnumDef("model_selection",
                    items=model_enum,
                    default="__none__",
                    label="Model(s) to publish",
                    tooltip="Select models to publish"),
        ]

    def create(self, subset_name, instance_data, pre_create_data):
        self.log.debug("CreateMatchMove.create")
        super().create(subset_name, instance_data, pre_create_data)
