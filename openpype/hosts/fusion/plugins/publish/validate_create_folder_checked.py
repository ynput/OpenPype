import pyblish.api

from openpype.pipeline.publish import RepairAction
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateCreateFolderChecked(pyblish.api.InstancePlugin):
    """Valid if all savers have the input attribute CreateDir checked on

    This attribute ensures that the folders to which the saver will write
    will be created.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Create Folder Checked"
    families = ["render", "image"]
    hosts = ["fusion"]
    actions = [RepairAction, SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        tool = instance.data["tool"]
        create_dir = tool.GetInput("CreateDir")
        if create_dir == 0.0:
            cls.log.error(
                "%s has Create Folder turned off" % instance[0].Name
            )
            return [tool]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Found Saver with Create Folder During Render checked off",
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for tool in invalid:
            tool.SetInput("CreateDir", 1.0)
