"""This module is used for command line publishing of image sequences."""

import os
import sys
import argparse
import logging
import subprocess
import platform

try:
    from shutil import which
except ImportError:
    # we are in python < 3.3
    def which(command):
        path = os.getenv('PATH')
        for p in path.split(os.path.pathsep):
            p = os.path.join(p, command)
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

handler = logging.basicConfig()
log = logging.getLogger("Publish Image Sequences")
log.setLevel(logging.DEBUG)

error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"


def __main__():

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
    # we need to use `auto_pype_root` to be able to remap locations.
    # This is egg and chicken case: we need to know our storage locations
    # to be able to remap them on different platforms but if we got `PYPE_ROOT`
    # variable, we cannot be sure it originated on different platform and is
    # therefor invalid.
    # So we use auto_pype_root to get to `PypeLauncher.path_remapper()`. This
    # will load Storage environments and is able to remap environment to
    # correct paths.
    sys.path.append(auto_pype_root)
    try:
        from pypeapp import PypeLauncher
    except ImportError:
        print("!!! Error: cannot determine Pype location.")
        print("--- we are looking at {}, but this is not Pype.".format(
            auto_pype_root))

    remapped_env = PypeLauncher.path_remapper()
    auto_pype_root = remapped_env.get('PYPE_ROOT') or auto_pype_root
    if remapped_env.get('PYPE_ROOT'):
        print("Got Pype location from environment: {}".format(
            remapped_env.get('PYPE_ROOT')))

    pype_command = "pype.ps1"
    if platform.system().lower() == "linux":
        pype_command = "pype"
    elif platform.system().lower() == "windows":
        pype_command = "pype.bat"

    if kwargs.pype:
        pype_root = kwargs.pype
    else:
        # test if pype.bat / pype is in the PATH
        # if it is, which() will return its path and we use that.
        # if not, we use auto_pype_root path. Caveat of that one is
        # that it can be UNC path and that will not work on windows.

        pype_path = which(pype_command)

        if pype_path:
            pype_root = os.path.dirname(pype_path)
        else:
            pype_root = auto_pype_root

    print("Set pype root to: {}".format(pype_root))
    print("Paths: {}".format(kwargs.paths or [os.getcwd()]))

    paths = kwargs.paths or [os.getcwd()]

    args = [
        os.path.join(pype_root, pype_command),
        "publish",
        " ".join(paths)
    ]

    print("Pype command: {}".format(" ".join(args)))
    # Forcing forwaring the environment because environment inheritance does
    # not always work.
    # Cast all values in environment to str to be safe
    env = {k: str(v) for k, v in remapped_env.items()}
    exit_code = subprocess.call(args, env=env)
    if exit_code != 0:
        raise RuntimeError("Publishing failed.")


if __name__ == '__main__':
    __main__()
