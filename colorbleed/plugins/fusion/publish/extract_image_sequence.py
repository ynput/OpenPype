import os
import glob
import re

import pyblish.api

_frame_regex = re.compile("[0-9]")


class ExtractImageSequence(pyblish.api.Extractor):
    """Extract result of saver by starting a comp render

    This will run the local render of Fusion,
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Image Sequence"
    families = ["colorbleed.imagesequence"]
    hosts = ["fusion"]

    def process(self, context):

        current_comp = context.data["currentComp"]
        start_frame = current_comp.GetAttrs("COMPN_RenderStart")
        end_frame = current_comp.GetAttrs("COMPN_RenderEnd")

        # todo: read more about Render table form, page 84
        # todo: Think out strategy, create renderSettings instance?
        # Build Fusion Render Job

        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(start_frame))
        self.log.info("End frame: {}".format(end_frame))

        result = current_comp.Render()
        if result:

            # Get all output paths after render was successful
            # Note the .ID check, this is to ensure we only have savers
            instances = [i for i in context[:] if i[0].ID == "Saver"]
            for instance in instances:
                # Ensure each instance has its files for the integrator
                output_path = instance.data["path"]
                query = self._create_qeury(output_path)
                files = glob.glob(query)

                if "files" not in instance.data:
                    instance.data["files"] = list()

                print("{} files : {}".format(instance.data["subset"],
                                             len(files)))
                instance.data["files"].append(files)

                # Ensure the integrator has stagingDir
                instance.data["stagingDir"] = os.path.dirname(output_path)

    def _create_qeury(self, instance):
        """Create a queriable string for glob

        Args:
            instance: instance of current context (comp)

        Returns:
            str
        """

        clipname = instance.data["path"]
        clip_dir = os.path.dirname(clipname)
        basename = os.path.basename(clipname)
        _, ext = os.path.splitext(basename)

        match = re.match("([0-9]{4})", basename)
        if not match:
            query_name = "{}.*.{}".format(instance.data["subset"], ext[1:])
        else:
            query_name = basename.replace(match.group(0), ".*.")

        query = os.path.join(clip_dir, query_name)

        return query
