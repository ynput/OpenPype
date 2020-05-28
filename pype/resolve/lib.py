import sys
from .utils import get_resolve_module

self = sys.modules[__name__]
self.pm = None


def get_project_manager():
    if not self.pm:
        resolve = get_resolve_module()
        self.pm = resolve.GetProjectManager()
    return self.pm
