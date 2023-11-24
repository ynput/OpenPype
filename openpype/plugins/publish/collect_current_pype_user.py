import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.lib import get_openpype_username


class CollectCurrentUserPype(pyblish.api.ContextPlugin):
    """Inject the currently logged on user into the Context"""

    # Order must be after default pyblish-base CollectCurrentUser
    order = pyblish.api.CollectorOrder + 0.001
    label = (
        "Collect AYON User"
        if AYON_SERVER_ENABLED
        else "Collect OpenPype User"
    )

    def process(self, context):
        user = get_openpype_username()
        context.data["user"] = user
        self.log.debug("Collected user \"{}\"".format(user))
