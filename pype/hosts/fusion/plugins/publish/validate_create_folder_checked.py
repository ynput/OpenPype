import pyblish.api

from pype import action


class ValidateCreateFolderChecked(pyblish.api.InstancePlugin):
    """Valid if all savers have the input attribute CreateDir checked on

    This attribute ensures that the folders to which the saver will write
    will be created.
    """

    order = pyblish.api.ValidatorOrder
    actions = [action.RepairAction]
    label = "Validate Create Folder Checked"
    families = ["render"]
    hosts = ["fusion"]

    @classmethod
    def get_invalid(cls, instance):
        active = instance.data.get("active", instance.data.get("publish"))
        if not active:
            return []

        tool = instance[0]
        create_dir = tool.GetInput("CreateDir")
        if create_dir == 0.0:
            cls.log.error("%s has Create Folder turned off" % instance[0].Name)
            return [tool]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found Saver with Create Folder During "
                               "Render checked off")

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for tool in invalid:
            tool.SetInput("CreateDir", 1.0)
