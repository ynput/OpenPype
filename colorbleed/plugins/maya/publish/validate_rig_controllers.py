import logging

from maya import cmds

import pyblish.api
import colorbleed.api

log = logging.getLogger("Rig Controllers")


class ValidateRigControllers(pyblish.api.InstancePlugin):
    """Check if the controllers have the transformation attributes set to
    default values, locked vibisility attributes and are not keyed
    """
    order = colorbleed.api.ValidateContentsOrder + 0.05
    label = "Rig Controllers"
    hosts = ["maya"]
    families = ["colorbleed.rig"]
    actions = [colorbleed.api.RepairAction,
               colorbleed.api.SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError('{} failed, see log '
                               'information'.format(self.label))

    @classmethod
    def get_invalid(cls, instance):

        error = False
        invalid = []
        is_keyed = list()
        not_locked = list()
        is_offset = list()

        controls = cmds.sets("controls_SET", query=True)
        assert controls, "Must have controls in rig controls_SET"

        for control in controls:
            valid_keyed = cls.validate_keyed_state(control)
            if not valid_keyed:
                is_keyed.append(control)

            # check if visibility is locked
            attribute = "{}.visibility".format(control)
            locked = cmds.getAttr(attribute, lock=True)
            if not locked:
                not_locked.append(control)

            valid_transforms = cls.validate_transforms(control)
            if not valid_transforms:
                is_offset.append(control)

        if is_keyed:
            cls.log.error("No controls can be keyes. Failed :\n"
                           "%s" % is_keyed)
            error = True

        if is_offset:
            cls.log.error("All controls default transformation values. "
                           "Failed :\n%s" % is_offset)
            error = True

        if not_locked:
            cls.log.error("All controls must have visibility "
                           "attribute locked. Failed :\n"
                           "%s" % not_locked)
            error = True

        if error:
            invalid = is_keyed + not_locked + is_offset
            cls.log.error("Invalid rig controllers. See log for details.")

        return invalid

    @staticmethod
    def validate_transforms(control):
        tolerance = 1e-30
        identity = [1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]

        matrix = cmds.xform(control, query=True, matrix=True, objectSpace=True)
        if not all(abs(x - y) < tolerance for x, y in zip(identity, matrix)):
            log.error("%s matrix : %s" % (control, matrix))
            return False
        return True

    @staticmethod
    def validate_keyed_state(control):
        """Check if the control has an animation curve attached
        Args:
            control:

        Returns:

        """
        animation_curves = cmds.keyframe(control, query=True, name=True)
        if animation_curves:
            return False
        return True

    @classmethod
    def repair(cls, instance):

        identity = [1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0]

        # lock all controllers in controls_SET
        controls = cmds.sets("controls_SET", query=True)
        for control in controls:
            log.info("Repairing visibility")
            attr = "{}.visibility".format(control)
            locked = cmds.getAttr(attr, lock=True)
            if not locked:
                log.info("Locking visibility for %s" % control)
                cmds.setAttr(attr, lock=True)

            log.info("Repairing matrix")
            if not cls.validate_transforms(control):
                cmds.xform(control, matrix=identity, objectSpace=True)
