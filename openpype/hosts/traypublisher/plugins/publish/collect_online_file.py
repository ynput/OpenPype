# -*- coding: utf-8 -*-
import pyblish.api
from pathlib import Path


class CollectSettingsSimpleInstances(pyblish.api.InstancePlugin):
    """Collect online file and retain its file name."""
    label = "Collect online file"
    families = ["online"]
    hosts = ["traypublisher"]

    def process(self, instance):
        file = Path(instance.data["creator_attributes"]["path"])

        if not instance.data.get("representations"):
            instance.data["representations"] = [
                {
                    "name": file.suffix.lstrip("."),
                    "ext": file.suffix.lstrip("."),
                    "files": file.name,
                    "stagingDir": file.parent.as_posix()
                }
            ]

