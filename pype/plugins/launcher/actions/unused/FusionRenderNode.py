import os
from avalon import api, lib


class FusionRenderNode(api.Action):

    name = "fusionrendernode9"
    label = "F9 Render Node"
    icon = "object-group"
    order = 997

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_PROJECT" in session:
            return False
        return True

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered

        Args:
            session (dict): environment dictionary

        Returns:
            Popen instance of newly spawned process

        """

        # Update environment with session
        env = os.environ.copy()
        env.update(session)

        # Get executable by name
        app = lib.get_application(self.name)
        env.update(app["environment"])
        executable = lib.which(app["executable"])

        return lib.launch(executable=executable, args=[], environment=env)
