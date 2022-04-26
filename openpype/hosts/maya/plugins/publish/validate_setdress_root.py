
import pyblish.api
import openpype.api


class ValidateSetdressRoot(pyblish.api.InstancePlugin):
    """
    """

    order = openpype.api.ValidateContentsOrder
    label = "SetDress Root"
    hosts = ["maya"]
    families = ["setdress"]

    def process(self, instance):
        from maya import cmds

        if instance.data.get("exactSetMembersOnly"):
            return

        set_member = instance.data["setMembers"]
        root = cmds.ls(set_member, assemblies=True, long=True)

        if not root or root[0] not in set_member:
            raise Exception("Setdress top root node is not being published.")
