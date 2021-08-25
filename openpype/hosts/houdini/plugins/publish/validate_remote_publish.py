import pyblish.api
import openpype.api

from openpype.hosts.houdini.api import lib

import hou


class ValidateRemotePublishOutNode(pyblish.api.ContextPlugin):
    """Validate the remote publish out node exists for Deadline to trigger."""

    order = pyblish.api.ValidatorOrder - 0.4
    families = ["*"]
    hosts = ["houdini"]
    targets = ["deadline"]
    label = "Remote Publish ROP node"
    actions = [openpype.api.RepairContextAction]

    def process(self, context):

        cmd = "import colorbleed.lib; colorbleed.lib.publish_remote()"

        node = hou.node("/out/REMOTE_PUBLISH")
        if not node:
            raise RuntimeError("Missing REMOTE_PUBLISH node.")

        # We ensure it's a shell node and that it has the pre-render script
        # set correctly. Plus the shell script it will trigger should be
        # completely empty (doing nothing)
        assert node.type().name() == "shell", "Must be shell ROP node"
        assert node.parm("command").eval() == "", "Must have no command"
        assert not node.parm("shellexec").eval(), "Must not execute in shell"
        assert (
            node.parm("prerender").eval() == cmd
        ), "REMOTE_PUBLISH node does not have correct prerender script."
        assert (
            node.parm("lprerender").eval() == "python"
        ), "REMOTE_PUBLISH node prerender script type not set to 'python'"

    @classmethod
    def repair(cls, context):
        """(Re)create the node if it fails to pass validation."""
        lib.create_remote_publish_node(force=True)
