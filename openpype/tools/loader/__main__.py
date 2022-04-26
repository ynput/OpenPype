"""Main entrypoint for standalone debugging

    Used for running 'avalon.tool.loader.__main__' as a module (-m), useful for
    debugging without need to start host.

    Modify AVALON_MONGO accordingly
"""
import os
import sys
from . import cli


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


if __name__ == '__main__':
    os.environ["OPENPYPE_MONGO"] = "mongodb://localhost:27017"
    os.environ["AVALON_DB"] = "avalon"
    os.environ["AVALON_TIMEOUT"] = "1000"
    os.environ["OPENPYPE_DEBUG"] = "1"
    os.environ["AVALON_ASSET"] = "Jungle"

    # Set the exception hook to our wrapping function
    sys.excepthook = my_exception_hook

    sys.exit(cli(sys.argv[1:]))
