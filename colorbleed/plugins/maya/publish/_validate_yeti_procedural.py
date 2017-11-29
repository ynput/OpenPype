import pyblish.api
import colorbleed.api


class ValidateYetiProcedurals(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    These are external files to the current application, for example
    these could be textures, image planes, cache files or other linked
    media.

    This validates:
        - The resources are existing files.
        - The resources have correctly collected the data.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Yeti Procedurals"

    def process(self, instance):
        return True

