from maya import cmds

import pyblish.api

import pype.api
import pype.hosts.maya.action
from pype.hosts.maya.lib import undo_chunk


class ValidateRigControllers(pyblish.api.InstancePlugin):
    """Validate rig controllers.

    Controls must have the transformation attributes on their default
    values of translate zero, rotate zero and scale one when they are
    unlocked attributes.

    Unlocked keyable attributes may not have any incoming connections. If
    these connections are required for the rig then lock the attributes.

    The visibility attribute must be locked.

    Note that `repair` will:
        - Lock all visibility attributes
        - Reset all default values for translate, rotate, scale
        - Break all incoming connections to keyable attributes

    """
    order = pype.api.ValidateContentsOrder + 0.05
    label = "Rig Controllers"
    hosts = ["maya"]
    families = ["rig"]
    actions = [pype.api.RepairAction,
               pype.hosts.maya.action.SelectInvalidAction]

    # Default controller values
    CONTROLLER_DEFAULTS = {
        "translateX": 0,
        "translateY": 0,
        "translateZ": 0,
        "rotateX": 0,
        "rotateY": 0,
        "rotateZ": 0,
        "scaleX": 1,
        "scaleY": 1,
        "scaleZ": 1
    }

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError('{} failed, see log '
                               'information'.format(self.label))

    @classmethod
    def get_invalid(cls, instance):

        controllers_sets = [i for i in instance if i == "controls_SET"]
        controls = cmds.sets(controllers_sets, query=True)
        assert controls, "Must have 'controls_SET' in rig instance"

        # Ensure all controls are within the top group
        lookup = set(instance[:])
        assert all(control in lookup for control in cmds.ls(controls,
                                                            long=True)), (
            "All controls must be inside the rig's group."
        )

        # Validate all controls
        has_connections = list()
        has_unlocked_visibility = list()
        has_non_default_values = list()
        for control in controls:
            if cls.get_connected_attributes(control):
                has_connections.append(control)

            # check if visibility is locked
            attribute = "{}.visibility".format(control)
            locked = cmds.getAttr(attribute, lock=True)
            if not locked:
                has_unlocked_visibility.append(control)

            if cls.get_non_default_attributes(control):
                has_non_default_values.append(control)

        if has_connections:
            cls.log.error("Controls have input connections: "
                          "%s" % has_connections)

        if has_non_default_values:
            cls.log.error("Controls have non-default values: "
                          "%s" % has_non_default_values)

        if has_unlocked_visibility:
            cls.log.error("Controls have unlocked visibility "
                          "attribute: %s" % has_unlocked_visibility)

        invalid = []
        if (has_connections or
                has_unlocked_visibility or
                has_non_default_values):
            invalid = set()
            invalid.update(has_connections)
            invalid.update(has_non_default_values)
            invalid.update(has_unlocked_visibility)
            invalid = list(invalid)
            cls.log.error("Invalid rig controllers. See log for details.")

        return invalid

    @classmethod
    def get_non_default_attributes(cls, control):
        """Return attribute plugs with non-default values

        Args:
            control (str): Name of control node.

        Returns:
            list: The invalid plugs

        """

        invalid = []
        for attr, default in cls.CONTROLLER_DEFAULTS.items():
            if cmds.attributeQuery(attr, node=control, exists=True):
                plug = "{}.{}".format(control, attr)

                # Ignore locked attributes
                locked = cmds.getAttr(plug, lock=True)
                if locked:
                    continue

                value = cmds.getAttr(plug)
                if value != default:
                    cls.log.warning("Control non-default value: "
                                    "%s = %s" % (plug, value))
                    invalid.append(plug)

        return invalid

    @staticmethod
    def get_connected_attributes(control):
        """Return attribute plugs with incoming connections.

        This will also ensure no (driven) keys on unlocked keyable attributes.

        Args:
            control (str): Name of control node.

        Returns:
            list: The invalid plugs

        """
        import maya.cmds as mc

        # Support controls without any attributes returning None
        attributes = mc.listAttr(control, keyable=True, scalar=True) or []
        invalid = []
        for attr in attributes:
            plug = "{}.{}".format(control, attr)

            # Ignore locked attributes
            locked = cmds.getAttr(plug, lock=True)
            if locked:
                continue

            # Ignore proxy connections.
            if cmds.addAttr(plug, query=True, usedAsProxy=True):
                continue

            # Check for incoming connections
            if cmds.listConnections(plug, source=True, destination=False):
                invalid.append(plug)

        return invalid

    @classmethod
    def repair(cls, instance):

        # Use a single undo chunk
        with undo_chunk():
            controls = cmds.sets("controls_SET", query=True)
            for control in controls:

                # Lock visibility
                attr = "{}.visibility".format(control)
                locked = cmds.getAttr(attr, lock=True)
                if not locked:
                    cls.log.info("Locking visibility for %s" % control)
                    cmds.setAttr(attr, lock=True)

                # Remove incoming connections
                invalid_plugs = cls.get_connected_attributes(control)
                if invalid_plugs:
                    for plug in invalid_plugs:
                        cls.log.info("Breaking input connection to %s" % plug)
                        source = cmds.listConnections(plug,
                                                      source=True,
                                                      destination=False,
                                                      plugs=True)[0]
                        cmds.disconnectAttr(source, plug)

                # Reset non-default values
                invalid_plugs = cls.get_non_default_attributes(control)
                if invalid_plugs:
                    for plug in invalid_plugs:
                        attr = plug.split(".")[-1]
                        default = cls.CONTROLLER_DEFAULTS[attr]
                        cls.log.info("Setting %s to %s" % (plug, default))
                        cmds.setAttr(plug, default)
