from pype import api as pype
from pypeapp import Anatomy, config


log = pype.Logger().get_logger(__name__, "nuke")


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
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("nuke.templates.get_node_dataflow_preset(): \
               Missing mandatory kwargs `host`, `cls`")

    nuke_dataflow = get_dataflow_preset().get(str(host), None)
    nuke_dataflow_nodes = nuke_dataflow.get('nodes', None)
    nuke_dataflow_node = nuke_dataflow_nodes.get(str(cls), None)

    if preset:
        nuke_dataflow_node = nuke_dataflow_node.get(str(preset), None)

    log.info("Dataflow: {}".format(nuke_dataflow_node))
    return nuke_dataflow_node


def get_node_colorspace_preset(**kwarg):
    ''' Get preset data for colorspace
    '''
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("nuke.templates.get_node_colorspace_preset(): \
               Missing mandatory kwargs `host`, `cls`")

    nuke_colorspace = get_colorspace_preset().get(str(host), None)
    nuke_colorspace_node = nuke_colorspace.get(str(cls), None)
    if preset:
        nuke_colorspace_node = nuke_colorspace_node.get(str(preset), None)

    log.info("Colorspace: {}".format(nuke_colorspace_node))
    return nuke_colorspace_node
