from __future__ import annotations

import DaVinciResolveScript as bmd
import openpype.hosts.resolve.api as api


# NOTE: so yeah resolve object just can't be used as a superclass
# ! this acts as singleton
class ProjectManager(object):
    __root_object: object

    def __new__(cls, *args) -> object:
        if not hasattr(cls, "instance"):
            cls.instance = super(ProjectManager, cls).__new__(cls)
        cls.__root_object = bmd.scriptapp("Resolve").GetProjectManager()
        return cls.instance

    @property
    def root(cls):
        return cls.__root_object

    @property
    def projects(cls) -> list(str):
        return cls.root.GetProjectListInCurrentFolder()

    @property
    def current_project(self) -> api.Project:
        return api.Project(self.root.GetCurrentProject())
