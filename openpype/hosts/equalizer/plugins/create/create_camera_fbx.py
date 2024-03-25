from openpype.hosts.equalizer.api import EqualizerCreator


# Creating FBX camera

class CreateFBXCamera(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.camera"
    label = "Camera FBX"
    family = "cameraFBX"
    icon = "camera"
    default_variants = ["Main"]

    def create(self, subset_name, instance_data, pre_create_data):
        self.log.debug("CreateFBXCamera.create")
        super(CreateFBXCamera, self).create(subset_name, instance_data, pre_create_data)
