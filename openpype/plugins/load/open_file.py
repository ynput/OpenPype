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


class Openfile(load.LoaderPlugin):
    """Open Image Sequence with system default"""

    families = ["render2d"]
    representations = ["*"]

    label = "Open"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):
        import clique

        directory = os.path.dirname(self.fname)
        pattern = clique.PATTERNS["frames"]

        files = os.listdir(directory)
        representation = context["representation"]

        ext = representation["name"]
        path = representation["data"]["path"]

        if ext in ["#"]:
            collections, remainder = clique.assemble(files,
                                                     patterns=[pattern],
                                                     minimum_items=1)

            seqeunce = collections[0]

            first_image = list(seqeunce)[0]
            filepath = os.path.normpath(os.path.join(directory, first_image))
        else:
            file = [f for f in files
                    if ext in f
                    if "#" not in f][0]
            filepath = os.path.normpath(os.path.join(directory, file))

        self.log.info("Opening : {}".format(filepath))

        open(filepath)
