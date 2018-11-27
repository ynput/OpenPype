import os


from app.api import (Templates, Logger)

log = Logger.getLogger(__name__,
                       os.getenv("AVALON_APP", "pype-config"))


def load_data_from_templates():
    from . import api
    if not any([
        api.Dataflow,
        api.Anatomy,
        api.Colorspace,
        api.Metadata]
    ):
        # base = Templates()
        t = Templates(type=["anatomy", "metadata", "dataflow", "colorspace"])
        api.Anatomy = t.anatomy
        api.Metadata = t.metadata.format()
        data = {"metadata": api.Metadata}
        api.Dataflow = t.dataflow.format(data)
        api.Colorspace = t.colorspace
        log.info("Data from templates were Loaded...")


def reset_data_from_templates():
    from . import api
    api.Dataflow = None
    api.Anatomy = None
    api.Colorspace = None
    api.Metadata = None
    log.info("Data from templates were Unloaded...")
