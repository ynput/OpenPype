import os
import nuke
import pyblish.api


class CollectWorkfile(pyblish.api.InstancePlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder
    label = "Collect Workfile"
    hosts = ['nuke']
    families = ["workfile"]

    def process(self, instance):  # sourcery skip: avoid-builtin-shadow

        script_data = instance.context.data["scriptData"]
        current_file = os.path.normpath(nuke.root().name())

        # creating instances per write node
        staging_dir = os.path.dirname(current_file)
        base_name = os.path.basename(current_file)

        # creating representation
        representation = {
            'name': 'nk',
            'ext': 'nk',
            'files': base_name,
            "stagingDir": staging_dir,
        }

        # creating instance data
        instance.data.update({
            "name": base_name,
            "representations": [representation]
        })

        # adding basic script data
        instance.data.update(script_data)

        self.log.debug(
            "Collected current script version: {}".format(current_file)
        )
