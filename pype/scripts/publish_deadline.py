import os
import subprocess
import platform
import argparse


def __main__():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths",
                        nargs="*",
                        default=[],
                        help="The filepaths to publish. This can be a "
                             "directory or a path to a .json publish "
                             "configuration.")

    kwargs, args = parser.parse_known_args()
    pype_root = os.environ.get("PYPE_ROOT")
    if not pype_root:
        raise Exception("PYPE_ROOT is not set")

    # TODO: set correct path
    pype_command = "pype.bat"
    if platform.system().lower() == "linux":
        pype_command = "pype"
    args = [os.path.join(pype_root, pype_command),
            "--publish", "--paths", kwargs.paths]

    print('>>> running pype ...')
    p = subprocess.call(args, shell=True)
    print('<<< done [ {} ]'.format(p.returncode))
