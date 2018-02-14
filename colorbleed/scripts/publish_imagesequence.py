"""This module is used for command line publishing of image sequences."""

import os
import sys
import logging

handler = logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def publish(paths, gui=False):
    """Publish rendered image sequences based on the job data

    Args:
        paths (list): a list of paths where to publish from
        gui (bool, Optional): Choose to show Pyblish GUI, default is False

    Returns:
        None

    """

    assert isinstance(paths, (list, tuple)), "Must be list of paths"
    assert any(paths)
    # Set the paths to publish for the collector if any provided
    if paths:
        os.environ["IMAGESEQUENCES"] = os.pathsep.join(paths)

    # Install Avalon with shell as current host
    from avalon import api, shell
    api.install(shell)

    # Register target and host
    import pyblish.api
    pyblish.api.register_target("imagesequence")
    pyblish.api.register_host("shell")

    # Publish items
    if gui:
        import pyblish_qml
        pyblish_qml.show(modal=True)
    else:

        import pyblish.util
        context = pyblish.util.publish()

        if not context:
            log.warning("Nothing published.")
            sys.exit(1)


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

    print("Running publish imagesequence...")
    print("Paths: {}".format(kwargs.paths or [os.getcwd()]))
    publish(kwargs.paths, gui=kwargs.gui)


if __name__ == '__main__':
    __main__()
