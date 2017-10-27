import pyblish.api
import copy


class CollectMindbenderImageSequences(pyblish.api.ContextPlugin):
    """Gather image sequnences from working directory"""

    order = pyblish.api.CollectorOrder
    hosts = ["shell"]
    label = "Image Sequences"

    def process(self, context):
        import os
        import json
        from avalon.vendor import clique

        # Force towards a single json sequence (override searching
        # the current working directory)
        USE_JSON = os.environ.get("USE_JSON", "")
        if USE_JSON:
            workspace = os.path.dirname(USE_JSON)
            base = workspace
            dirs = [os.path.splitext(os.path.basename(USE_JSON))[0]]
        # Else use the current working directory
        else:
            workspace = context.data["workspaceDir"]
            base, dirs, _ = next(os.walk(workspace))

        for renderlayer in dirs:
            abspath = os.path.join(base, renderlayer)
            files = os.listdir(abspath)
            pattern = clique.PATTERNS["frames"]
            collections, remainder = clique.assemble(files,
                                                     patterns=[pattern],
                                                     minimum_items=1)
            assert not remainder, (
                "There shouldn't have been a remainder for '%s': "
                "%s" % (renderlayer, remainder))

            # Maya 2017 compatibility, it inexplicably prefixes layers
            # with "rs_" without warning.
            compatpath = os.path.join(base, renderlayer.split("rs_", 1)[-1])

            for fname in (abspath, compatpath):
                try:
                    with open("{}.json".format(fname)) as f:
                        metadata = json.load(f)
                    break

                except OSError:
                    continue

            else:
                raise Exception("%s was not published correctly "
                                "(missing metadata)" % renderlayer)

            metadat_instance = metadata['instance']
            # For now ensure this data is ignored
            for collection in collections:
                instance = context.create_instance(str(collection))
                self.log.info("Collection: %s" % list(collection))

                # Ensure each instance gets its own unique reference to
                # the source data
                instance_metadata = copy.deepcopy(metadat_instance)

                data = dict(instance_metadata, **{
                    "name": instance.name,
                    "family": "Image Sequence",
                    "families": ["colorbleed.imagesequence"],
                    "subset": collection.head[:-1],
                    "stagingDir": os.path.join(workspace, renderlayer),
                    "files": [list(collection)],
                    "metadata": metadata
                })

                instance.data.update(data)
