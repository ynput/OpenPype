import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateInstanceAssetRepair(pyblish.api.Action):
    """Repair the instance asset."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        pass


description = """
## Publish plugins

### Validate Scene Settings

#### Skip Resolution Check for Tasks

Set regex pattern(s) to look for in a Task name to skip resolution check against values from DB.

#### Skip Timeline Check for Tasks

Set regex pattern(s) to look for in a Task name to skip `frameStart`, `frameEnd` check against values from DB.

### AfterEffects Submit to Deadline

* `Use Published scene` - Set to True (green) when Deadline should take published scene as a source instead of uploaded local one.
* `Priority` - priority of job on farm
* `Primary Pool` - here is list of pool fetched from server you can select from.
* `Secondary Pool`
* `Frames Per Task` - number of sequence division between individual tasks (chunks)
making one job on farm.
"""


class ValidateWithError(pyblish.api.InstancePlugin):
    """Validate the instance asset is the current selected context asset.

        As it might happen that multiple worfiles are opened, switching
        between them would mess with selected context.
        In that case outputs might be output under wrong asset!

        Repair action will use Context asset value (from Workfiles or Launcher)
        Closing and reopening with Workfiles will refresh  Context value.
    """

    label = "Validate With Error"
    hosts = ["testhost"]
    actions = [ValidateInstanceAssetRepair]
    order = pyblish.api.ValidatorOrder

    def process(self, instance):
        raise PublishValidationError("Crashing", "Instance error", description)
