import os

from maya import cmds

import avalon.maya
import config.api


class ExtractMayaAsciiRaw(config.api.Extractor):
    """Extract as Maya Ascii (raw)

    This will preserve all references, construction history, etc.

    """

    label = "Maya ASCII (Raw)"
    hosts = ["maya"]
    families = ["config.mayaAscii"]

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Whether to include all nodes in the instance (including those from
        # history) or only use the exact set members
        members_only = instance.data.get("exactSetMembersOnly", False)
        if members_only:
            members = instance.data.get("setMembers", list())
            if not members:
                raise RuntimeError("Can't export 'exact set members only' "
                                   "when set is empty.")
        else:
            members = instance[:]

        # Perform extraction
        self.log.info("Performing extraction..")
        with avalon.maya.maintained_selection():
            cmds.select(members, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=True,
                      constructionHistory=True)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
