from openpype.hosts.equalizer.api import EqualizerCreator
from openpype.lib import NumberDef
from openpype.hosts.equalizer.api import EqualizerHost

class CreateLensDistortionData(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.lens_distortion"
    label = "Lens Distortion"
    family = "lensDistortion"
    icon = "glasses"

    def get_instance_attr_defs(self):
        overscan = EqualizerHost.get_host().get_overscan()
        if overscan:
            img_overscan_width, img_overscan_height = overscan.values()
        else:
            img_overscan_width, img_overscan_height = 100, 100
        
        return[
            NumberDef("overscan_percent_width",
                label="Overscan Width %",
                default=img_overscan_width,
                decimals=0,
                minimum=1,
                maximum=1000),
            NumberDef("overscan_percent_height",
                label="Overscan Height %",
                default=img_overscan_height,
                decimals=0,
                minimum=1,
                maximum=1000),
        ]
    def create(self, subset_name, instance_data, pre_create_data):
        super(CreateLensDistortionData, self).create(subset_name, instance_data, pre_create_data)
