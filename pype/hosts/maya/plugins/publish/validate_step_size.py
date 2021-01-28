import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateStepSize(pyblish.api.InstancePlugin):
    """Validates the step size for the instance is in a valid range.

    For example the `step` size should never be lower or equal to zero.

    """

    order = pype.api.ValidateContentsOrder
    label = 'Step size'
    families = ['camera',
                'pointcache',
                'animation']
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    MIN = 0.01
    MAX = 1.0

    @classmethod
    def get_invalid(cls, instance):

        objset = instance.data['name']
        step = instance.data.get("step", 1.0)

        if step < cls.MIN or step > cls.MAX:
            cls.log.warning("Step size is outside of valid range: {0} "
                            "(valid: {1} to {2})".format(step,
                                                         cls.MIN,
                                                         cls.MAX))
            return objset

        return []

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid instances found: {0}".format(invalid))
