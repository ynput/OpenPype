from openpype.hosts.gaffer.api.lib import make_box
from openpype.hosts.gaffer.api import plugin

import Gaffer


class CreateGafferNodes(plugin.GafferCreatorBase):
    identifier = "io.openpype.creators.gaffer.gaffernodes"
    label = "Gaffer Box"
    family = "gafferNodes"
    description = "Export Box node for referencing"
    icon = "gears"

    def _create_node(self,
                     subset_name: str,
                     pre_create_data: dict) -> Gaffer.Node:
        return make_box(subset_name)
