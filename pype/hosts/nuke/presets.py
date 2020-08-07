from pype.api import Anatomy, config, Logger
import nuke

log = Logger().get_logger(__name__, "nuke")


def get_anatomy(**kwarg):
    return Anatomy()


def get_dataflow_preset():
    presets = config.get_init_presets()
    return presets["dataflow"]


def get_colorspace_preset():
    presets = config.get_init_presets()
    return presets["colorspace"]


def get_node_dataflow_preset(**kwarg):
    ''' Get preset data for dataflow (fileType, compression, bitDepth)
    '''
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    families = kwarg.get("families", [])
    preset = kwarg.get("preset", None)  # omit < 2.0.0v

    assert any([host, cls]), nuke.message(
        "`{}`: Missing mandatory kwargs `host`, `cls`".format(__file__))

    nuke_dataflow = get_dataflow_preset().get(str(host), None)
    nuke_dataflow_nodes = nuke_dataflow.get('nodes', None)
    nuke_dataflow_node = nuke_dataflow_nodes.get(str(cls), None)

    if preset:  # omit < 2.0.0v
        nuke_dataflow_node = nuke_dataflow_node.get(str(preset), None)
        # omit < 2.0.0v

    if families:
        for family in families:
            nuke_dataflow_node = nuke_dataflow_node.get(str(family), None)

    log.info("Dataflow: {}".format(nuke_dataflow_node))
    return nuke_dataflow_node


def get_node_colorspace_preset(**kwarg):
    ''' Get preset data for colorspace
    '''
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    families = kwarg.get("families", [])
    preset = kwarg.get("preset", None)  # omit < 2.0.0v

    if not any([host, cls]):
        msg = "`{}`: Missing mandatory kwargs `host`, `cls`".format(__file__)
        log.error(msg)
        nuke.message(msg)

    nuke_colorspace = get_colorspace_preset().get(str(host), None)
    nuke_colorspace_node = nuke_colorspace.get(str(cls), None)

    if preset:  # omit < 2.0.0v
        nuke_colorspace_node = nuke_colorspace_node.get(str(preset), None)
        # omit < 2.0.0v

    if families:
        for family in families:
            nuke_colorspace_node = nuke_colorspace_node.get(str(family), None)

    log.info("Colorspace: {}".format(nuke_colorspace_node))
    return nuke_colorspace_node
