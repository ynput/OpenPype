# -*- coding: utf-8 -*-
import pyblish.api
import hou

class ValidateAlembicROPFaceSets(pyblish.api.InstancePlugin):
    """Validate Face Sets are disabled for extraction to pointcache.

    When groups are saved as Face Sets with the Alembic these show up
    as shadingEngine connections in Maya - however, with animated groups
    these connections in Maya won't work as expected, it won't update per
    frame. Additionally, it can break shader assignments in some cases
    where it requires to first break this connection to allow a shader to
    be assigned.

    It is allowed to include Face Sets, so only an issue is logged to
    identify that it could introduce issues down the pipeline.

    """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["abc"]
    hosts = ["houdini"]
    label = "Validate Alembic ROP Face Sets"

    def process(self, instance):

        rop = instance.data["transientData"]["instance_node"]
        facesets = rop.parm("facesets").eval()

        # 0 = No Face Sets
        # 1 = Save Non-Empty Groups as Face Sets
        # 2 = Save All Groups As Face Sets
        if facesets != 0:
            self.log.warning(
                "Alembic ROP saves 'Face Sets' for Geometry. "
                "Are you sure you want this?"
            )
