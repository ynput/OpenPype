"""This module is used for command line publishing of image sequences."""

import os
import sys
import logging
import subprocess
import platform

handler = logging.basicConfig()
log = logging.getLogger("Publish Image Sequences")
log.setLevel(logging.DEBUG)

error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"


def __main__():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths",
                        nargs="*",
                        default=[],
                        help="The filepaths to publish. This can be a "
                             "directory or a path to a .json publish "
                             "configuration.")
    parser.add_argument("--gui",
                        default=False,
                        action="store_true",
                        help="Whether to run Pyblish in GUI mode.")

    kwargs, args = parser.parse_known_args()

    print("Running pype ...")
    pype_root = os.path.dirname(os.path.abspath(__file__))
    pype_root = os.path.abspath(pype_root + "../../../../..")
    pype_root = os.environ.get('PYPE_ROOT') or pype_root
    print("Set pype root to: {}".format(pype_root))
    print("Paths: {}".format(kwargs.paths or [os.getcwd()]))

    pype_command = "pype.bat"
    if platform.system().lower() == "linux":
        pype_command = "pype"

    paths = kwargs.paths or [os.getcwd()]
    print("Pype command: {}".format(os.path.join(pype_root, pype_command)))
    subprocess.call([os.path.join(pype_root, pype_command),
                     "--ignore", "--publish", "--paths",
                     " ".join(paths)], shell=True)


if __name__ == '__main__':
    __main__()
