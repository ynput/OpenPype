import os
import getpass
import pyblish.api


class CollectCurrentUserPype(pyblish.api.ContextPlugin):
    """Inject the currently logged on user into the Context"""

    # Order must be after default pyblish-base CollectCurrentUser
    order = pyblish.api.CollectorOrder + 0.001
    label = "Collect Pype User"

    def process(self, context):
        user = os.getenv("PYPE_USERNAME", "").strip()
        if not user:
            return

        context.data["user"] = user
        self.log.debug("Pype user is \"{}\"".format(user))
