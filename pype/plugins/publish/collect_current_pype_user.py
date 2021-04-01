import os
import getpass
import pyblish.api


class CollectCurrentUserPype(pyblish.api.ContextPlugin):
    """Inject the currently logged on user into the Context"""

    # Order must be after default pyblish-base CollectCurrentUser
    order = pyblish.api.CollectorOrder + 0.001
    label = "Collect Pype User"

    def process(self, context):
        user = os.getenv("OPENPYPE_USERNAME", "").strip()
        if not user:
            user = context.data.get("user", getpass.getuser())

        context.data["user"] = user
        self.log.debug("Colected user \"{}\"".format(user))
