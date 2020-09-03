# -*- coding: utf-8 -*-
"""Create instance of vrayscene."""
import avalon.maya


class CreateVRayScene(avalon.maya.Creator):
    """Create Vray Scene."""

    label = "VRay Scene"
    family = "vrayscene"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        """Entry."""
        super(CreateVRayScene, self).__init__(*args, **kwargs)

        self.data["exportOnFarm"] = False
