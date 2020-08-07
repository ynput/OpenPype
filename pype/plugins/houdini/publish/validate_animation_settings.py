import pyblish.api

from pype.hosts.houdini import lib


class ValidateAnimationSettings(pyblish.api.InstancePlugin):
    """Validate if the unexpanded string contains the frame ('$F') token

    This validator will only check the output parameter of the node if
    the Valid Frame Range is not set to 'Render Current Frame'

    Rules:
        If you render out a frame range it is mandatory to have the
        frame token - '$F4' or similar - to ensure that each frame gets
        written. If this is not the case you will override the same file
        every time a frame is written out.

    Examples:
        Good: 'my_vbd_cache.$F4.vdb'
        Bad: 'my_vbd_cache.vdb'

    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Frame Settings"
    families = ["vdbcache"]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Output settings do no match for '%s'" %
                               instance)

    @classmethod
    def get_invalid(cls, instance):

        node = instance[0]

        # Check trange parm, 0 means Render Current Frame
        frame_range = node.evalParm("trange")
        if frame_range == 0:
            return []

        output_parm = lib.get_output_parameter(node)
        unexpanded_str = output_parm.unexpandedString()

        if "$F" not in unexpanded_str:
            cls.log.error("No frame token found in '%s'" % node.path())
            return [instance]
