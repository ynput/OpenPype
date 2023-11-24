import tde4

from openpype.hosts.equalizer.api import EqualizerCreator
from openpype.lib import EnumDef


class CreateLensDistortionData(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.lens_distortion"
    label = "Lens Distortion"
    family = "lensDistortion"
    icon = "glasses"

    def create(self, subset_name, instance_data, pre_create_data):
        super().create(subset_name, instance_data, pre_create_data)
