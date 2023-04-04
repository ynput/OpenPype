# -*- coding: utf-8 -*-
import pyblish.api
from pathlib import Path


class CollectAudio(pyblish.api.InstancePlugin):
    """Collect audio file."""
    label = "Collect Audio"
    order = pyblish.api.CollectorOrder
    families = ["audio"]
    hosts = ["traypublisher"]

    def process(self, instance):
        file = Path(instance.data["path"])
        instance.data["representations"].append(
            {
                "name": file.suffix.lstrip("."),
                "ext": file.suffix.lstrip("."),
                "files": file.name,
                "stagingDir": file.parent.as_posix()
            }
        )
