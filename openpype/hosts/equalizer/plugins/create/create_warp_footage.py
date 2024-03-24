from openpype.hosts.equalizer.api import EqualizerCreator

class CreateWarpFootage(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.warp_footage"
    label = "Warp Footage"
    family = "warpFootage"
    icon = "image"

    def create(self, subset_name, instance_data, pre_create_data):
        super(CreateWarpFootage, self).create(subset_name, instance_data, pre_create_data)
