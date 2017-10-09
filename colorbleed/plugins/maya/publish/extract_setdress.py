import json

import os

import colorbleed.api
from colorbleed.maya.lib import extract_alembic

from maya import cmds


class ExtractSetDress(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Set Dress"
    hosts = ["maya"]
    families = ["colorbleed.setdress"]

    def process(self, instance):

        # Dump json
        self.log.info("Dumping scene data for debugging ..")

        data = instance.data

        self.log.info("Extracting point cache")

        parent_dir = self.staging_dir(instance)
        filename = "{}.abc".format(instance.name)
        path = os.path.join(parent_dir, filename)
        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(parent_dir, json_filename)

        with open(json_path, "w") as fp:
            json.dump(data["scenedata"], fp, ensure_ascii=False, indent=4)

        cmds.select(instance)

        # Run basic alembic exporter
        extract_alembic(file=path,
                        startFrame=1.0,
                        endFrame=1.0,
                        **{"step": 1.0,
                           "attr": ["cbId"],
                           "writeVisibility": True,
                           "writeCreases": True,
                           "uvWrite": True,
                           "selection": True})

        instance.data["files"] = [json_path, path]
