import pyblish.api


class CollectMindbenderImageSequences(pyblish.api.ContextPlugin):
    """Gather image sequnences from working directory"""

    order = pyblish.api.CollectorOrder
    hosts = ["shell"]
    label = "Image Sequences"

    def process(self, context):
        import os
        import json
        from avalon.vendor import clique

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

            for collection in collections:
                instance = context.create_instance(str(collection))
                self.log.info("Collection: %s" % list(collection))

                data = dict(metadata["instance"], **{
                    "name": instance.name,
                    "family": "Image Sequences",
                    "families": ["colorbleed.imagesequence"],
                    "subset": collection.head[:-1],
                    "stagingDir": os.path.join(workspace, renderlayer),
                    "files": [list(collection)],
                    "metadata": metadata
                })

                instance.data.update(data)
