"""This module is used for command line publishing of image sequences."""

import os
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

    parser.add_argument("--pype", help="Pype root")

    kwargs, args = parser.parse_known_args()

    print("Running pype ...")
    auto_pype_root = os.path.dirname(os.path.abspath(__file__))
    auto_pype_root = os.path.abspath(auto_pype_root + "../../../../..")
    auto_pype_root = os.environ.get('PYPE_ROOT') or auto_pype_root

    if kwargs.pype:
        pype_root = kwargs.pype
    else:
        # if pype argument not specified, lets assume it is set in PATH
        pype_root = ""

    print("Set pype root to: {}".format(pype_root))
    print("Paths: {}".format(kwargs.paths or [os.getcwd()]))

    paths = kwargs.paths or [os.getcwd()]
    pype_command = "pype.ps1"
    if platform.system().lower() == "linux":
        pype_command = "pype"
    elif platform.system().lower() == "windows":
        pype_command = "pype.bat"

    args = [
        os.path.join(pype_root, pype_command),
        "publish",
        " ".join(paths)
    ]

    print("Pype command: {}".format(" ".join(args)))
    # Forcing forwaring the environment because environment inheritance does
    # not always work.
    exit_code = subprocess.call(args, env=os.environ)
    if exit_code != 0:
        raise ValueError("Publishing failed.")


if __name__ == '__main__':
    __main__()
