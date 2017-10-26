"""
This module is used for command line publishing of image sequences.
Due to its early intergration this module might change location within the
config. It is also subject to change

Contributors:
    Roy Nieterau
    Wijnand Koreman

Dependencies:
    Avalon
    Pyblish

"""

import os
import sys
import json
import logging

handler = logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def publish_data(json_file):
    """Publish rendered image sequences based on the job data

    Args:
        json_file (str): the json file of the data dump of the submitted job

    Returns:
        None

    """
    with open(json_file, "r") as fp:
        json_data = json.load(fp)

    # Get the job's environment
    job = json_data["jobs"][0]
    job_env = job["Props"]["Env"]
    job_env = {str(key): str(value) for key, value in job_env.items()}

    # Ensure the key exists
    os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "")

    # Add the pythonpaths (also to sys.path for local session)
    pythonpaths = job_env.pop("PYTHONPATH", "").split(";")
    for path in pythonpaths:
        sys.path.append(path)

    os.environ['PYTHONPATH'] += ";" + ";".join(pythonpaths)

    # Use the rest of the job's environment
    os.environ.update(job_env)

    # Set the current pyblish host
    os.environ["PYBLISH_HOSTS"] = "shell"

    # Set the current working directory
    os.chdir(os.path.dirname(json_file))

    # Install Avalon with shell as current host
    from avalon import api, shell
    api.install(shell)

    # Publish items, returns context instances
    import pyblish.util
    context = pyblish.util.publish()

    if not context:
        log.warning("Nothing published.")
        sys.exit(1)


def __main__():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="The filepath of the JSON")

    kwargs, args = parser.parse_known_args()

    if kwargs.path:
        filepath = os.path.normpath(kwargs.path)
        print("JSON File {}".format(filepath))
        if not filepath.endswith(".json"):
            raise RuntimeError("Wrong extesion! Expecting publish data to be "
                               "stored in a .JSON file")

        publish_data(filepath)


# this is needed to ensure Deadline can run the script
if __name__ == '__main__':
    __main__()
