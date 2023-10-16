import os
import logging
import runpy

import pyblish.api
import pyblish.util

from openpype.pipeline import registered_host
from openpype.host import IPublishHost

log = logging.getLogger(__name__)


def run_path(path):
    """Run Python script by filepath with current globals"""
    return runpy.run_path(path, init_globals=globals())


def main():
    host = registered_host()
    assert host, "Host must already be installed and registered."

    # Get required inputs
    filepath = os.environ["PUBLISH_WORKFILE"]

    # Get optional inputs
    pre_publish_scripts = [
        script for script in
        os.environ.get("PUBLISH_PRE_SCRIPTS", "").split(os.pathsep)
        if script.strip()
    ]
    post_publish_scripts = [
        script for script in
        os.environ.get("PUBLISH_POST_SCRIPTS", "").split(os.pathsep)
        if script.strip()
    ]

    # TODO: What to do if a host does not auto-install? How to know which host
    #  install to trigger? Can we reliably defer maybe for all hosts?
    if not host:
        host = registered_host()
        assert host, "Must have a registered host active."

    # Open workfile, the application should've been launched with the matching
    # context for that workfile
    log.info("Opening workfile: %s", filepath)
    host.open_file(filepath)

    for script in pre_publish_scripts:
        log.info("Running pre-publish script: %s", script)
        run_path(script)

    # Trigger publish, catch errors
    success = publish()

    for script in post_publish_scripts:
        log.info("Running post-publish script: %s", script)
        run_path(script)

    if not success:
        raise RuntimeError("Errors occurred during publishing.")


def publish():
    """Trigger headless publish in host

    Returns:
        bool: Whether publish finished successfully without errors
    """
    # Perform headless publish
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

    host = registered_host()
    is_new_publisher = isinstance(host, IPublishHost)
    if is_new_publisher:
        # New publisher host
        # TODO: Test this functionality
        from openpype.pipeline.create import CreateContext
        create_context = CreateContext(host)

        # TODO: Allow to tweak any values on existing instances
        # if tweak_instances_fn:
        #     tweak_instances_fn(create_context.instances)
        #     create_context.save_changes()
        #     create_context.reset()

        pyblish_context = pyblish.api.Context()
        pyblish_context.data["create_context"] = create_context
        pyblish_plugins = create_context.publish_plugins
    else:
        # Legacy publisher host
        pyblish_context = pyblish.api.Context()  # pyblish default behavior
        pyblish_plugins = pyblish.api.discover()  # pyblish default behavior

    # TODO: Allow a validation to occur and potentially allow certain "Actions"
    #   to trigger on Validators (or other plugins?) if they exist

    for result in pyblish.util.publish_iter(
            context=pyblish_context,
            plugins=pyblish_plugins
    ):
        for record in result["records"]:
            log.info("{}: {}".format(result["plugin"].label, record.msg))

        # Exit as soon as any error occurs.
        if result["error"]:
            # TODO: For new style publisher we only want to DIRECTLY stop
            #  on any error if it's not a Validation error, otherwise we'd want
            #  to report all validation errors
            error_message = error_format.format(**result)
            log.error(error_message)
            return False

    return True


if __name__ == "__main__":
    log.debug("Starting publish script...")
    main()
