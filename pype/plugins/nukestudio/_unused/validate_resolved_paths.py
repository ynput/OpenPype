from pyblish import api

class ValidateResolvedPaths(api.ContextPlugin):
    """Validate there are no overlapping resolved paths."""

    order = api.ValidatorOrder
    label = "Resolved Paths"
    hosts = ["nukestudio"]

    def process(self, context):
        import os
        import collections

        paths = []
        for instance in context:
            if "trackItem.task" == instance.data["family"]:
                paths.append(
                    os.path.abspath(instance.data["task"].resolvedExportPath())
                )

        duplicates = []
        for item, count in collections.Counter(paths).items():
            if count > 1:
                duplicates.append(item)

        msg = "Duplicate output paths found: {0}".format(duplicates)
        assert not duplicates, msg
