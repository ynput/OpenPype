#!/usr/bin/env python
import time
from pype.hosts.resolve.utils import get_resolve_module
from pype.api import Logger

log = Logger().get_logger(__name__, "resolve")

wait_delay = 2.5
wait = 0.00
ready = None
while True:
    try:
        # Create project and set parameters:
        resolve = get_resolve_module()
        pm = resolve.GetProjectManager()
        if pm:
            ready = None
        else:
            ready = True
    except AttributeError:
        pass

    if ready is None:
        time.sleep(wait_delay)
        log.info(f"Waiting {wait}s for Resolve to have opened Project Manager")
        wait += wait_delay
    else:
        print(f"Preloaded variables: \n\n\tResolve module: "
              f"`resolve` > {type(resolve)} \n\tProject manager: "
              f"`pm` > {type(pm)}")
        break
