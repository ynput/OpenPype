import os
import importlib
from pyblish import api as pyblish
from avalon import api
import logging


log = logging.getLogger(__name__)

AVALON_CONFIG = os.environ["AVALON_CONFIG"]


def ls():
    pass


def reload_pipeline():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    api.uninstall()

    for module in ("avalon.io",
                   "avalon.lib",
                   "avalon.pipeline",
                   "avalon.api",
                   "avalon.tools",

                   "avalon.tools.loader.app",
                   "avalon.tools.creator.app",
                   "avalon.tools.manager.app",

                   "avalon.premiere",
                   "avalon.premiere.pipeline",
                   "{}".format(AVALON_CONFIG)
                   ):
        log.info("Reloading module: {}...".format(module))
        module = importlib.import_module(module)
        reload(module)

    import avalon.premiere
    api.install(avalon.premiere)


def install(config):
    """Install Premiere-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into Premiere.

    It is called automatically when installing via `api.install(premiere)`.

    See the Maya equivalent for inspiration on how to implement this.

    """

    pyblish.register_host("premiere")
    # Trigger install on the config's "premiere" package
    config = find_host_config(config)

    if hasattr(config, "install"):
        config.install()

    log.info("config.premiere installed")


def find_host_config(config):
    try:
        config = importlib.import_module(config.__name__ + ".premiere")
    except ImportError as exc:
        if str(exc) != "No module name {}".format(
                config.__name__ + ".premiere"):
            raise
        config = None

    return config


def uninstall(config):
    """Uninstall all tha was installed

    This is where you undo everything that was done in `install()`.
    That means, removing menus, deregistering families and  data
    and everything. It should be as though `install()` was never run,
    because odds are calling this function means the user is interested
    in re-installing shortly afterwards. If, for example, he has been
    modifying the menu or registered families.

    """
    config = find_host_config(config)
    if hasattr(config, "uninstall"):
        config.uninstall()

    pyblish.deregister_host("premiere")


def get_anatomy(**kwarg):
    return pype.Anatomy


def get_dataflow(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "premiere")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("premiera.lib.get_dataflow():"
                                       "Missing mandatory kwargs `host`, `cls`")

    pr_dataflow = getattr(pype.Dataflow, str(host), None)
    pr_dataflow_node = getattr(pr_dataflow.nodes, str(cls), None)
    if preset:
        pr_dataflow_node = getattr(pr_dataflow_node, str(preset), None)

    log.info("Dataflow: {}".format(pr_dataflow_node))
    return pr_dataflow_node


def get_colorspace(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "premiere")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("premiera.templates.get_colorspace():"
                                       "Missing mandatory kwargs `host`, `cls`")

    pr_colorspace = getattr(pype.Colorspace, str(host), None)
    pr_colorspace_node = getattr(pr_colorspace, str(cls), None)
    if preset:
        pr_colorspace_node = getattr(pr_colorspace_node, str(preset), None)

    log.info("Colorspace: {}".format(pr_colorspace_node))
    return pr_colorspace_node
