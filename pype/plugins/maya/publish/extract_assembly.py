import json

import os

import pype.api
from pype.maya.lib import extract_alembic

from maya import cmds


class ExtractAssembly(pype.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Assembly"
    hosts = ["maya"]
    families = ["assembly"]

    def process(self, instance):

        parent_dir = self.staging_dir(instance)
        hierarchy_filename = "{}.abc".format(instance.name)
        hierarchy_path = os.path.join(parent_dir, hierarchy_filename)
        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(parent_dir, json_filename)

        self.log.info("Dumping scene data for debugging ..")
        with open(json_path, "w") as filepath:
            json.dump(instance.data["scenedata"], filepath, ensure_ascii=False)

        self.log.info("Extracting point cache ..")
        cmds.select(instance.data["hierarchy"])

        # Run basic alembic exporter
        extract_alembic(file=hierarchy_path,
                        startFrame=1.0,
                        endFrame=1.0,
                        **{"step": 1.0,
                           "attr": ["cbId"],
                           "writeVisibility": True,
                           "writeCreases": True,
                           "uvWrite": True,
                           "selection": True})

        instance.data["files"] = [json_filename, hierarchy_filename]

        # Remove data
        instance.data.pop("scenedata", None)

        cmds.select(clear=True)
