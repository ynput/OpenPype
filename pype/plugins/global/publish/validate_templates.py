import pyblish.api
from app.api import (
    Templates
)

class ValidateTemplates(pyblish.api.ContextPlugin):
    """Check if all templates were filed"""

    label = "Validate Templates"
    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya", "houdini", "nuke"]

    def process(self, context):

        anatomy = context.data["anatomy"]
        if not anatomy:
            raise RuntimeError("Did not find templates")
        else:
            data = { "project": {"name": "D001_projectsx",
                                "code": "prjX"},
                     "representation": "exr",
                     "version": 3,
                     "task": "animation",
                     "asset": "sh001",
                     "hierarchy": "ep101/sq01/sh010"}


            anatomy = context.data["anatomy"].format(data)
            self.log.info(anatomy.work.path)

            data = { "project": {"name": "D001_projectsy",
                                "code": "prjY"},
                     "representation": "abc",
                     "version": 1,
                     "task": "lookdev",
                     "asset": "bob",
                     "hierarchy": "ep101/sq01/bob"}

            anatomy = context.data["anatomy"].format(data)
            self.log.info(anatomy.work.file)
