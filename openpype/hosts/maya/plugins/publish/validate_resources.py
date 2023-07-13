import os
from collections import defaultdict

import pyblish.api
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateResources(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    These are external files to the current application, for example
    these could be textures, image planes, cache files or other linked
    media.

    This validates:
        - The resources have unique filenames (without extension)

    """

    order = ValidateContentsOrder
    label = "Resources Unique"

    def process(self, instance):

        resources = instance.data.get("resources", [])
        if not resources:
            self.log.debug("No resources to validate..")
            return

        basenames = defaultdict(set)

        for resource in resources:
            files = resource.get("files", [])
            for filename in files:

                # Use normalized paths in comparison and ignore case
                # sensitivity
                filename = os.path.normpath(filename).lower()

                basename = os.path.splitext(os.path.basename(filename))[0]
                basenames[basename].add(filename)

        invalid_resources = list()
        for basename, sources in basenames.items():
            if len(sources) > 1:
                invalid_resources.extend(sources)

                self.log.error(
                    "Non-unique resource name: {0}"
                    "{0} (sources: {1})".format(
                        basename,
                        list(sources)
                    )
                )

        if invalid_resources:
            raise PublishValidationError("Invalid resources in instance.")
