#!/usr/bin/env python
import time
from python_get_resolve import GetResolve

wait_delay = 2.5
wait = 0.00
ready = None
while True:
    try:
        # Create project and set parameters:
        resolve = GetResolve()
        PM = resolve.GetProjectManager()
        P = PM.GetCurrentProject()
        if P.GetName() == "Untitled Project":
            ready = None
        else:
            ready = True
    except AttributeError:
        pass

    if ready is None:
        time.sleep(wait_delay)
        print(f"Waiting {wait}s for Resolve to be open inproject")
        wait += wait_delay
    else:
        break
