import pyblish.api
import pype.api

import os


class ValidateResources(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    These are external files to the current application, for example
    these could be textures, image planes, cache files or other linked
    media.

    This validates:
        - The resources are existing files.
        - The resources have correctly collected the data.

    """

    order = pype.api.ValidateContentsOrder
    label = "Resources"

    def process(self, instance):

        for resource in instance.data.get('resources', []):
            # Required data
            assert "source" in resource, "No source found"
            assert "files" in resource, "No files from source"
            assert all(os.path.exists(f) for f in resource['files'])
