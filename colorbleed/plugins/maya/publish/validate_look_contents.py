import pyblish.api
import colorbleed.api


class ValidateLookContents(pyblish.api.InstancePlugin):
    """Validate look instance contents

    This is invalid when the collection was unable to collect the required
    data for a look to be published correctly.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Contents'

    def process(self, instance):
        """Process all the nodes in the instance"""

        error = False

        attributes = ["sets",
                      "relationships",
                      "attributes"]

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        # Required look data
        lookdata = instance.data["lookData"]
        for attr in attributes:
            if attr not in lookdata:
                self.log.error("No %s found in data" % attr)
                error = True

        if error:
            raise RuntimeError("Invalid look content. See log for details.")
