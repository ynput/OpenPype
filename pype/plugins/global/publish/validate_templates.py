import pyblish.api
import os

class ValidateTemplates(pyblish.api.ContextPlugin):
    """Check if all templates were filed"""

    label = "Validate Templates"
    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya", "houdini", "nuke"]

    def process(self, context):

        anatomy = context.data["anatomy"]
        if not anatomy:
            raise RuntimeError("Did not find anatomy")
        else:
            data = {
                    "root": os.environ["PYPE_STUDIO_PROJECTS_PATH"],
                    "project": {"name": "D001_projectsx",
                                "code": "prjX"},
                     "ext": "exr",
                     "version": 3,
                     "task": "animation",
                     "asset": "sh001",
                     "hierarchy": "ep101/sq01/sh010"}


            anatomy_filled = anatomy.format(data)
            self.log.info(anatomy_filled)

            data = {"root": os.environ["PYPE_STUDIO_PROJECTS_PATH"],
                    "project": {"name": "D001_projectsy",
                                "code": "prjY"},
                     "ext": "abc",
                     "version": 1,
                     "task": "lookdev",
                     "asset": "bob",
                     "hierarchy": "ep101/sq01/bob"}

            anatomy_filled = context.data["anatomy"].format(data)
            self.log.info(anatomy_filled["work"]["folder"])
