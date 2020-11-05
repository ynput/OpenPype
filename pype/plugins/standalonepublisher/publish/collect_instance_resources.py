import os
import tempfile
import pyblish.api
from copy import deepcopy

class CollectInstanceResources(pyblish.api.InstancePlugin):
    """Collect instance's resources"""

    # must be after `CollectInstances`
    order = pyblish.api.CollectorOrder + 0.011
    label = "Collect Instance Resources"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    def process(self, instance):
        anatomy = instance.context.data["anatomy"]
        anatomy_data = deepcopy(instance.context.data["anatomyData"])
        anatomy_data.update({"root": anatomy.roots})

        subset = instance.data["subset"]
        clip_name = instance.data["clipName"]

        editorial_source_root = instance.data["editorialSourceRoot"]
        editorial_source_path = instance.data["editorialSourcePath"]

        if editorial_source_path:
            # add family if mov or mp4 found which is longer for
            # cutting `trimming` to enable `ExtractTrimmingVideoAudio` plugin
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data["stagingDir"] = staging_dir
            instance.data["families"] += ["trimming"]
            return

        if "{" in editorial_source_root:
            editorial_source_root = editorial_source_root.format(
                **anatomy_data)

        self.log.debug(f"root: {editorial_source_root}")

        for root, dirs, files in os.walk(editorial_source_root):
            if subset in root and clip_name in root:
                staging_dir = root

        self.log.debug(f"staging_dir: {staging_dir}")


        # add `editorialSourceRoot`  as staging dir

        # if `editorialSourcePath` is none then loop
        # trough `editorialSourceRoot`

        # if image sequence then create representation > match
        # with subset name in dict

        # idenfify as image sequence `isSequence` on instance data
