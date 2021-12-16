"""Launch process that is not child process of python or OpenPype.

This is written for linux distributions where process tree may affect what
is when closed or blocked to be closed.
"""

import os
import sys
import subprocess
import json


def main(input_json_path):
    """Read launch arguments from json file and launch the process.

    Expected that json contains "args" key with string or list of strings.

    Arguments are converted to string using `list2cmdline`. At the end is added
    `&` which will cause that launched process is detached and running as
    "background" process.

    ## Notes
    @iLLiCiT: This should be possible to do with 'disown' or double forking but
        I didn't find a way how to do it properly. Disown didn't work as
        expected for me and double forking killed parent process which is
        unexpected too.
    """
    with open(input_json_path, "r") as stream:
        data = json.load(stream)

    # Change environment variables
    env = data.get("env") or {}
    for key, value in env.items():
        os.environ[key] = value

    # Prepare launch arguments
    args = data["args"]
    if isinstance(args, list):
        args = subprocess.list2cmdline(args)

    # Run the command as background process
    shell_cmd = args + " &"
    os.system(shell_cmd)
    sys.exit(0)


if __name__ == "__main__":
    # Expect that last argument is path to a json with launch args information
    main(sys.argv[-1])
