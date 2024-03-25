from openpype.hosts.equalizer.api import EqualizerCreator


# Creating undistorted footage camera

class CreateUNDCamera(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.footage"
    label = "Undistorted Footage"
    family = "lensDistortion"
    icon = "camera"
    default_variants = ["Main"]

    def create(self, subset_name, instance_data, pre_create_data):
        self.log.debug("CreateUNDCamera.create")

        super(CreateUNDCamera, self).create(subset_name, instance_data, pre_create_data)
