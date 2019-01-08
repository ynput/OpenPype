from pype import api as pype

log = pype.Logger.getLogger(__name__, "editorial")


def get_anatomy(**kwarg):
    return pype.Anatomy


def get_dataflow(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "editorial")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("premiera.templates.get_dataflow():"
                                       "Missing mandatory kwargs `host`, `cls`")

    edtr_dataflow = getattr(pype.Dataflow, str(host), None)
    edtr_dataflow_node = getattr(edtr_dataflow.nodes, str(cls), None)
    if preset:
        edtr_dataflow_node = getattr(edtr_dataflow_node, str(preset), None)

    log.info("Dataflow: {}".format(edtr_dataflow_node))
    return edtr_dataflow_node


def get_colorspace(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "editorial")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("editorial.templates.get_colorspace():"
                                       "Missing mandatory kwargs `host`, `cls`")

    edtr_colorspace = getattr(pype.Colorspace, str(host), None)
    edtr_colorspace_node = getattr(edtr_colorspace, str(cls), None)
    if preset:
        edtr_colorspace_node = getattr(edtr_colorspace_node, str(preset), None)

    log.info("Colorspace: {}".format(edtr_colorspace_node))
    return edtr_colorspace_node
