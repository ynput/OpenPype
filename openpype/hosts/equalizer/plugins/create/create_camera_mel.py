from openpype.hosts.equalizer.api import EqualizerCreator

from openpype.lib import BoolDef, EnumDef


# Creating MEL cameras

class CreateMELCamera(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.cameramel"
    label = "Camera MEL"
    family = "cameraMEL"
    icon = "camera"
    default_variants = ["Main"]

    def get_instance_attr_defs(self):
        return [
            EnumDef("export_mode",
                    label="Export",
                    items=[
                        "Current Camera Only",
                        "Selected Cameras Only",
                        "Sequence Cameras Only",
                        "References Cameras Only",
                        "All Cameras"
                    ],
                    default="Current Camera Only"
                    ),
            BoolDef(
                "undistorted_footage", label="Distortion", default=False
            )
        ]

    def create(self, subset_name, instance_data, pre_create_data):
        self.log.debug("CreateMELCamera.create")
        super(CreateMELCamera, self).create(subset_name, instance_data, pre_create_data)
