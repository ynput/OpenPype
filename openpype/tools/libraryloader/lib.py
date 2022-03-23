import os
import importlib
import logging

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
