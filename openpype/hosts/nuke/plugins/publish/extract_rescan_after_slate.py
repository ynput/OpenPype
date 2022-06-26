import os
import clique
import pyblish.api


class RescanAfterSlate(pyblish.api.InstancePlugin):
    """Rescans extracted representations after slate.
    Helps integration consistency if files were added
    during the slate extraction step, since the
    Representation file list and collection gets
    collected only once before it.
    """
    label = 'Rescan Repre After Slate'
    order = pyblish.api.ExtractorOrder + 0.005
    families = ["slate"]
    hosts = ['nuke']

    def process(self, instance):

        for repre in instance.data["representations"]:

            if isinstance(repre["files"], str):
                return

            self.log.debug("Current representation: {0}".format(repre))
            self.log.debug("Current collection: {0}".format(
                instance.data["collection"]
            ))

            staged_files = os.listdir(repre["stagingDir"])

            collected_frames = [x for x in staged_files if repre["ext"] in x]

            if len(repre["files"]) < len(collected_frames):
                self.log.debug(
                    "Found more files in staging than in representation," +
                    " updating with new files (slate frame)..."
                )
                repre["files"] = collected_frames
                collections, remainder = clique.assemble(collected_frames)
                if collections:
                    instance.data["collection"] = collections[0]
                self.log.debug("Rescanned representation: {0}".format(repre))
                self.log.debug("Rescanned collection: {0}".format(
                    instance.data["collection"]
                ))
            else:
                self.log.debug("No range issue found, moving on...")
