from openpype.hosts.houdini.api import plugin
from openpype.hosts.houdini.api import lib


class CreateRemotePublish(plugin.Creator):
    """Create Remote Publish Submission Settings node."""

    label = "Remote Publish"
    family = "remotePublish"
    icon = "cloud-upload"

    def process(self):
        """This is a stub creator process.

         This does not create a regular instance that the instance collector
         picks up. Instead we force this one to solely create something we
         explicitly want to create. The only reason this class is here is so
         that Artists can also create the node through the Avalon creator.

         """
        lib.create_remote_publish_node(force=True)
