from maya import cmds

import pyblish.api


class CollectMayaHistory(pyblish.api.InstancePlugin):
    """Collect history for instances from the Maya scene

    Note:
        This removes render layers collected in the history

    This is separate from Collect Instances so we can target it towards only
    specific family types.

    """

    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["maya"]
    label = "Maya History"
    families = ["rig"]
    verbose = False

    def process(self, instance):

        # Collect the history with long names
        history = cmds.listHistory(instance, leaf=False) or []
        history = cmds.ls(history, long=True)

        # Remove invalid node types (like renderlayers)
        invalid = cmds.ls(history, type="renderLayer", long=True)
        if invalid:
            invalid = set(invalid)  # optimize lookup
            history = [x for x in history if x not in invalid]

        # Combine members with history
        members = instance[:] + history
        members = list(set(members))    # ensure unique

        # Update the instance
        instance[:] = members
