import sys
import os
import subprocess

from openpype.pipeline import load


def open(filepath):
    """Open file with system default executable"""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


class OpenFile(load.LoaderPlugin):
    """Open Image Sequence or Video with system default"""

    families = ["render2d"]
    representations = ["*"]

    label = "Open"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):

        path = self.fname
        if not os.path.exists(path):
            raise RuntimeError("File not found: {}".format(path))

        self.log.info("Opening : {}".format(path))
        open(path)
