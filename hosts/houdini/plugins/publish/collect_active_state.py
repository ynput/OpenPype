import pyblish.api


class CollectInstanceActiveState(pyblish.api.InstancePlugin):
    """Collect default active state for instance from its node bypass state.

    This is done at the very end of the CollectorOrder so that any required
    collecting of data iterating over instances (with InstancePlugin) will
    actually collect the data for when the user enables the state in the UI.
    Otherwise potentially required data might have skipped collecting.

    """

    order = pyblish.api.CollectorOrder + 0.299
    families = ["*"]
    hosts = ["houdini"]
    label = "Instance Active State"

    def process(self, instance):

        # Must have node to check for bypass state
        if len(instance) == 0:
            return

        # Check bypass state and reverse
        active = True
        node = instance[0]
        if hasattr(node, "isBypassed"):
            active = not node.isBypassed()

        # Set instance active state
        instance.data.update(
            {
                "active": active,
                # temporarily translation of `active` to `publish` till
                # issue has been resolved:
                # https://github.com/pyblish/pyblish-base/issues/307
                "publish": active,
            }
        )
