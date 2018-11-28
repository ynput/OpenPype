from pype import api as pype

log = pype.Logger.getLogger(__name__, "nuke")


def get_dataflow(**kwarg):
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("cls", None)
    family = kwarg.get("family", None)
    assert any([host, cls]), log.error("nuke.templates.get_dataflow():"
                                       "Missing mandatory kwargs `host`, `cls`")

    nuke_dataflow = getattr(pype.Dataflow, str(host), None)
    nuke_dataflow_node = getattr(nuke_dataflow.nodes, str(cls), None)
    if family:
        nuke_dataflow_node = getattr(nuke_dataflow_node, str(family), None)

    log.info("Dataflow: {}".format(nuke_dataflow_node))
    return nuke_dataflow_node


def get_colorspace(**kwarg):
    host = kwarg.get("host", "nuke")
    cls = kwarg.get("cls", None)
    family = kwarg.get("family", None)
    assert any([host, cls]), log.error("nuke.templates.get_colorspace():"
                                       "Missing mandatory kwargs `host`, `cls`")

    nuke_colorspace = getattr(pype.Colorspace, str(host), None)
    nuke_colorspace_node = getattr(nuke_colorspace, str(cls), None)
    if family:
        nuke_colorspace_node = getattr(nuke_colorspace_node, str(family), None)

    log.info("Colorspace: {}".format(nuke_colorspace_node))
    return nuke_colorspace_node
