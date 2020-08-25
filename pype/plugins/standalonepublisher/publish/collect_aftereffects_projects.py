import copy
import glob
import os
from pprint import pformat

import pyblish.api


class CollectAftereffectsProjects(pyblish.api.InstancePlugin):
    """Collect After Effects Projects"""

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect After Effects Projects"
    hosts = ["standalonepublisher"]
    families = ["scene"]
    extensions = ["aep", "aepx"]

    # presets
    ignored_instance_data_keys = ("name", "label", "stagingDir", "version")

    def process(self, instance):
        context = instance.context
        asset_data = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        anatomy_data = instance.context.data["anatomyData"]
        repres = instance.data["representations"]
        staging_dir = repres[0]["stagingDir"]
        files = repres[0]["files"]
        ext = os.path.splitext(files)[-1]

        if ext in ("aep", "aepx"):
             pass
