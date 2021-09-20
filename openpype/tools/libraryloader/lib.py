import os
import importlib
import logging
from openpype.api import Anatomy

log = logging.getLogger(__name__)


# `find_config` from `pipeline`
def find_config():
    log.info("Finding configuration for project..")

    config = os.environ["AVALON_CONFIG"]

    if not config:
        raise EnvironmentError(
            "No configuration found in "
            "the project nor environment"
        )

    log.info("Found %s, loading.." % config)
    return importlib.import_module(config)


class RegisteredRoots:
    roots_per_project = {}

    @classmethod
    def registered_root(cls, project_name):
        if project_name not in cls.roots_per_project:
            cls.roots_per_project[project_name] = Anatomy(project_name).roots

        return cls.roots_per_project[project_name]
