from pype import api as pype

log = pype.Logger.getLogger(__name__, "premiere")


def get_anatomy(**kwarg):
    return pype.Anatomy


def get_dataflow(**kwarg):
    log.info(kwarg)
    host = kwarg.get("host", "premiere")
    cls = kwarg.get("class", None)
    preset = kwarg.get("preset", None)
    assert any([host, cls]), log.error("premiera.templates.get_dataflow():"
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
