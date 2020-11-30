import os
import pyblish.api
from pype.hosts import resolve
from avalon import api as avalon


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 0.501

    def process(self, context):
        exported_projet_ext = ".drp"
        asset = avalon.Session["AVALON_ASSET"]
        staging_dir = os.getenv("AVALON_WORKDIR")
        subset = "workfile"

        project = resolve.get_current_project()
        name = project.GetName()

        base_name = name + exported_projet_ext
        current_file = os.path.join(staging_dir, base_name)
        current_file = os.path.normpath(current_file)

        active_sequence = resolve.get_current_sequence()
        video_tracks = resolve.get_video_track_names()

        # set main project attributes to context
        context.data["activeProject"] = project
        context.data["activeSequence"] = active_sequence
        context.data["videoTracks"] = video_tracks
        context.data["currentFile"] = current_file

        self.log.info("currentFile: {}".format(current_file))

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
