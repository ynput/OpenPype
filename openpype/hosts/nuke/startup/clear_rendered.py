import os

from openpype.lib import Logger


def clear_rendered(dir_path):
    log = Logger.get_logger(__name__)

    for _f in os.listdir(dir_path):
        _f_path = os.path.join(dir_path, _f)
        log.info("Removing: `{}`".format(_f_path))
        os.remove(_f_path)
