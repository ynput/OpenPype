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

        kwargs = {}
        if int(cmds.about(version=True)) >= 2020:
            # New flag since Maya 2020 which makes cmds.listHistory faster
            kwargs = {"fastIteration": True}
        else:
            self.log.debug("Ignoring `fastIteration` flag before Maya 2020..")

        # Collect the history with long names
        history = set(cmds.listHistory(instance, leaf=False, **kwargs) or [])
        history = cmds.ls(list(history), long=True)

        # Exclude invalid nodes (like renderlayers)
        exclude = cmds.ls(type="renderLayer", long=True)
        if exclude:
            exclude = set(exclude)  # optimize lookup
            history = [x for x in history if x not in exclude]

        # Combine members with history
        members = instance[:] + history
        members = list(set(members))    # ensure unique

        # Update the instance
        instance[:] = members
