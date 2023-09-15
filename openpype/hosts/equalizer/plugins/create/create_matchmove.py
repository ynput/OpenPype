from openpype.hosts.equalizer.api import EqualizerCreator
from openpype.lib import BoolDef


class CreateMatchMove(EqualizerCreator):
    identifier = "io.openpype.creators.equalizer.matchmove"
    label = "Match Move"
    family = "matchmove"
    icon = "camera"

    def create(self, subset_name, instance_data, pre_create_data):
        self.log.debug("CreateMatchMove.create")
