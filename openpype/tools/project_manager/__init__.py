"""Project Manager tool

Purpose of the tool is to be able create and modify hierarchy under project
ready for OpenPype pipeline usage. Tool also give ability to create new
projects.

# Brief info
Project hierarchy consist of two types "asset" and "task". Assets can be
children of Project or other Asset. Task can be children of Asset.

It is not possible to have duplicated Asset name across whole project.
It is not possible to have duplicated Task name under one Asset.

Asset can't be moved or renamed if has or it's children has published content.

Deleted assets are not deleted from database but their type is changed to
"archived_asset".

Tool allows to modify Asset attributes like frame start/end, fps, etc.
"""

from .project_manager import (
    ProjectManagerWindow,
    main
)


__all__ = (
    "ProjectManagerWindow",
    "main"
)
