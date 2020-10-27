import os
import pyblish.api
from pype.hosts import hiero as phiero
from avalon import api as avalon


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        project = phiero.get_current_project()
        active_sequence = phiero.get_current_sequence()
        current_file = project.path()
        staging_dir = os.path.dirname(current_file)
        base_name = os.path.basename(current_file)

        # get main project attributes to context
        context.data["activeProject"] = project
        context.data["activeSequence"] = active_sequence
        context.data["currentFile"] = current_file
        self.log.info("currentFile: {}".format(current_file))
        asset = avalon.Session["AVALON_ASSET"]
        subset = "workfile"

        # creating workfile representation
        representation = {
            'name': 'hrox',
            'ext': 'hrox',
            'files': base_name,
            "stagingDir": staging_dir,
        }

        instance_data = {
            "name": "{}_{}".format(asset, subset),
            "asset": asset,
            "subset": "{}{}".format(asset, subset.capitalize()),
            "item": project,
            "family": "workfile",

            # source attribute
            "sourcePath": current_file,
            "representations": [representation]
        }

        instance = context.create_instance(**instance_data)
        self.log.info("Creating instance: {}".format(instance))
