import os

import pyblish.api

from avalon.vendor import clique


class ExtractImageSequence(pyblish.api.Extractor):
    """Extract result of saver by starting a comp render

    This will run the local render of Fusion,
    """

    order = pyblish.api.ExtractorOrder
    label = "Render Local"
    families = ["colorbleed.imagesequence"]
    hosts = ["fusion"]
    targets = ["renderlocal"]

    def process(self, context):

        current_comp = context.data["currentComp"]
        start_frame = current_comp.GetAttrs("COMPN_RenderStart")
        end_frame = current_comp.GetAttrs("COMPN_RenderEnd")

        # Build Fusion Render Job
        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(start_frame))
        self.log.info("End frame: {}".format(end_frame))

        result = current_comp.Render()
        if result:

            # Get all output paths after render was successful
            # Note the .ID check, this is to ensure we only have savers
            # Use instance[0] to get the tool
            instances = [i for i in context[:] if i[0].ID == "Saver"]
            for instance in instances:

                # Ensure each instance has its files for the integrator
                output_path = os.path.dirname(instance.data["path"])
                files = os.listdir(output_path)
                pattern = clique.PATTERNS["frames"]
                collections, remainder = clique.assemble(files,
                                                         patterns=[pattern],
                                                         minimum_items=1)

                assert not remainder, ("There should be no remainder for '%s': "
                                       "%s" % (instance.data["subset"],
                                               remainder))

                # Filter collections to ensure specific files are part of
                # the instance, store instance's collection
                if "files" not in instance.data:
                    instance.data["files"] = list()

                subset = instance.data["subset"]
                collection = next((c for c in collections if
                                   c.head[:-1] == subset), None)
                # for c in collections:
                #     name = c.head
                #     if name[-1] == ".":
                #         name = name[:-1]
                #
                #     if name == subset:
                #         collection = c
                #         break

                assert collection, "No collection found, this is a bug"

                # Add found collection to the instance
                instance.data["files"].append(list(collection))

                # Ensure the integrator has stagingDir
                instance.data["stagingDir"] = output_path
