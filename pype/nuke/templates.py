from pype import api as pype

log = pype.Logger().get_logger(__name__, "nuke")


def get_anatomy(**kwarg):
    return pype.Anatomy


def get_dataflow(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("nuke.templates.get_dataflow():"
                                       "Missing mandatory kwargs `host`, `cls`")

    nuke_dataflow = pype.Dataflow.get(str(host), None)
    nuke_dataflow_nodes = nuke_dataflow.get('nodes', None)
    nuke_dataflow_node = nuke_dataflow_nodes.get(str(cls), None)

    if preset:
        nuke_dataflow_node = nuke_dataflow_node.get(str(preset), None)

    log.info("Dataflow: {}".format(nuke_dataflow_node))
    return nuke_dataflow_node


def get_colorspace(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("nuke.templates.get_colorspace():"
                                       "Missing mandatory kwargs `host`, `cls`")

    nuke_colorspace = pype.Colorspace.get(str(host), None)
    nuke_colorspace_node = nuke_colorspace.get(str(cls), None)
    if preset:
        nuke_colorspace_node = nuke_colorspace_node.get(str(preset), None)

    log.info("Colorspace: {}".format(nuke_colorspace_node))
    return nuke_colorspace_node
