from pype import api as pype

log = pype.Logger.getLogger(__name__, "nuke")


def get_anatomy(**kwarg):
    return pype.Anatomy


def get_dataflow(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("nuke.templates.get_dataflow():"
                                       "Missing mandatory kwargs `host`, `cls`")

    nuke_dataflow = getattr(pype.Dataflow, str(host), None)
    nuke_dataflow_node = getattr(nuke_dataflow.nodes, str(cls), None)
    if preset:
        nuke_dataflow_node = getattr(nuke_dataflow_node, str(preset), None)

    log.info("Dataflow: {}".format(nuke_dataflow_node))
    return nuke_dataflow_node


def get_colorspace(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("nuke.templates.get_colorspace():"
                                       "Missing mandatory kwargs `host`, `cls`")

    nuke_colorspace = getattr(pype.Colorspace, str(host), None)
    nuke_colorspace_node = getattr(nuke_colorspace, str(cls), None)
    if preset:
        nuke_colorspace_node = getattr(nuke_colorspace_node, str(preset), None)

    log.info("Colorspace: {}".format(nuke_colorspace_node))
    return nuke_colorspace_node
