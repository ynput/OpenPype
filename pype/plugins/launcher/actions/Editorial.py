import os
import sys
from avalon import io
from pprint import pprint
import acre

from avalon import api, lib
import pype.api as pype

from pype.api import Logger

log = Logger.getLogger(__name__, "editorial")


class Editorial(api.Action):

    name = "editorial"
    label = "Pype Editorial Server"
    icon = "retweet"
    order = 996

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered

        Args:
            session (dict): environment dictionary

        Returns:
            Popen instance of newly spawned process

        """

        with pype.modified_environ(**session):
            # Get executable by name
            app = lib.get_application(self.name)
            executable = lib.which(app["executable"])

            # Run as server
            arguments = []

            tools_env = acre.get_tools([self.name])
            env = acre.compute(tools_env)
            env = acre.merge(env, current_env=dict(os.environ))

            if not env.get('AVALON_WORKDIR', None):
                pype.load_data_from_templates()
                os.environ["AVALON_WORKDIR"] = pype.make_workdir_path(
                    pype.Anatomy)
                pype.reset_data_from_templates()

            env.update(dict(os.environ))

            try:
                lib.launch(executable=executable,
                           args=arguments,
                           environment=env
                           )
            except Exception as e:
                log.error(e)
            return
