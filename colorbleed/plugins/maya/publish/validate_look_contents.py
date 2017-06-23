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

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        # Required look data
        assert "lookSets" in instance.data
        assert "lookSetRelations" in instance.data
        assert "lookAttributes" in instance.data
