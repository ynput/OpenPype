from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateRigControllers(pyblish.api.InstancePlugin):
    """Check if the controllers have the transformation attributes set to
    default values, locked vibisility attributes and are not keyed
    """
    order = colorbleed.api.ValidateContentsOrder + 0.05
    label = "Rig Controllers"
    hosts = ["maya"]
    families = ["colorbleed.rig"]

    def process(self, instance):

        error = False
        is_keyed = list()
        not_locked = list()
        is_offset = list()

        controls = cmds.sets("controls_SET", query=True)
        assert controls, "Must have controls in rig control_SET"

        for control in controls:
            valid_keyed = self.validate_keyed_state(control)
            if not valid_keyed:
                is_keyed.append(control)

            # check if visibility is locked
            attribute = "{}.visibility".format(control)
            locked = cmds.getAttr(attribute, lock=True)
            if not locked:
                not_locked.append(control)

            valid_transforms = self.validate_transforms(control)
            if not valid_transforms:
                is_offset.append(control)

        if is_keyed:
            self.log.error("No controls can be keyes. Failed :\n"
                           "%s" % is_keyed)

        if is_offset:
            self.log.error("All controls default transformation values. "
                           "Failed :\n%s" % is_offset)

        if not_locked:
            self.log.error("All controls must have visibility "
                           "attribute locked. Failed :\n"
                           "%s" % not_locked)

        if error:
            raise RuntimeError("Invalid rig controllers. See log for details.")

    def validate_transforms(self, control):
        tolerance = 1e-30
        identity = [1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]

        matrix = cmds.xform(control, query=True, matrix=True, objectSpace=True)
        if not all(abs(x - y) < tolerance for x, y in zip(identity, matrix)):
            return False
        return True

    def validate_keyed_state(self, control):
        """Check if the control has an animation curve attached
        Args:
            control:

        Returns:

        """
        animation_curves = cmds.keyframe(control, query=True, name=True)
        if animation_curves:
            return False
        return True
