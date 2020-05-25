#!/usr/bin/env python3.6
from python_get_resolve import GetResolve

resolve = GetResolve()
PM = resolve.GetProjectManager()
P = PM.GetCurrentProject()

print(P.GetName())
