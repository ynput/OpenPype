import os
import subprocess

import pyblish.api

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

    hosts = ['maya', 'fusion', 'nuke']
    families = [
        "renderlayer",
        "saver.deadline",
        "imagesequence"
    ]


    def process(self, context):
        """Inject the current working file"""
        user = None
        try:
            user = deadline_command("GetCurrentUserName").strip()
        except:
            self.log.warning("Deadline command seems not to be working")

        if not user:
            self.log.warning("No Deadline user found. "
                             "Do you have Deadline installed?")
            return

        self.log.info("Found Deadline user: {}".format(user))
        context.data['deadlineUser'] = user
