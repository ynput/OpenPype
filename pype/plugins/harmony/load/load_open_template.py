import tempfile
import zipfile
import os
import shutil

from avalon import api, harmony


class OpenTemplateLoader(api.Loader):
    """Open templates."""

    families = ["scene", "workfile"]
    representations = ["zip"]
    label = "Open Template"
    icon = "floppy-o"

    def load(self, context, name=None, namespace=None, data=None):
        # Open template.
        zip_file = api.get_representation_path(context["representation"])
        harmony.lib.launch_zip_file(zip_file)

        def update(self, container, representation):
            pass

        def remove(self, container):
            pass
