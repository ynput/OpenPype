"""
Requires:
    environment -> DEADLINE_PATH

Provides:
    context     -> deadlineUser (str)
"""

import os
import subprocess

import pyblish.api
from pype.plugin import contextplugin_should_run

CREATE_NO_WINDOW = 0x08000000


def deadline_command(cmd):
    # Find Deadline
    path = os.environ.get("DEADLINE_PATH", None)
    assert path is not None, "Variable 'DEADLINE_PATH' must be set"

    executable = os.path.join(path, "deadlinecommand")
    if os.name == "nt":
        executable += ".exe"
    assert os.path.exists(
        executable), "Deadline executable not found at %s" % executable
    assert cmd, "Must have a command"

    query = (executable, cmd)

    process = subprocess.Popen(query, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True,
                               creationflags=CREATE_NO_WINDOW)
    out, err = process.communicate()

    return out


class CollectDeadlineUser(pyblish.api.ContextPlugin):
    """Retrieve the local active Deadline user"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Deadline User"
    hosts = ['maya', 'fusion']
    families = ["renderlayer", "saver.deadline"]

    def process(self, context):
        """Inject the current working file"""

        # Workaround bug pyblish-base#250
        if not contextplugin_should_run(self, context):
            return

        user = deadline_command("GetCurrentUserName").strip()

        if not user:
            self.log.warning("No Deadline user found. "
                             "Do you have Deadline installed?")
            return

        self.log.info("Found Deadline user: {}".format(user))
        context.data['deadlineUser'] = user
