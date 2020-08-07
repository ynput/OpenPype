from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateCameraAttributes(pyblish.api.InstancePlugin):
    """Validates Camera has no invalid attribute keys or values.

    The Alembic file format does not a specifc subset of attributes as such
    we validate that no values are set there as the output will not match the
    current scene. For example the preScale, film offsets and film roll.

    """

    order = pype.api.ValidateContentsOrder
    families = ['camera']
    hosts = ['maya']
    label = 'Camera Attributes'
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    DEFAULTS = [
        ("filmFitOffset", 0.0),
        ("horizontalFilmOffset", 0.0),
        ("verticalFilmOffset", 0.0),
        ("preScale", 1.0),
        ("filmTranslateH", 0.0),
        ("filmTranslateV", 0.0),
        ("filmRollValue", 0.0)
    ]

    @classmethod
    def get_invalid(cls, instance):

        # get cameras
        members = instance.data['setMembers']
        shapes = cmds.ls(members, dag=True, shapes=True, long=True)
        cameras = cmds.ls(shapes, type='camera', long=True)

        invalid = set()
        for cam in cameras:

            for attr, default_value in cls.DEFAULTS:
                plug = "{}.{}".format(cam, attr)
                value = cmds.getAttr(plug)

                # Check if is default value
                if value != default_value:
                    cls.log.warning("Invalid attribute value: {0} "
                                    "(should be: {1}))".format(plug,
                                                               default_value))
                    invalid.add(cam)

                if cmds.listConnections(plug, source=True, destination=False):
                    # TODO: Validate correctly whether value always correct
                    cls.log.warning("%s has incoming connections, validation "
                                    "is unpredictable." % plug)

        return list(invalid)

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Invalid camera attributes: %s" % invalid)
