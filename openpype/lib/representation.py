# -*- coding: utf-8 -*-
"""Class for handling representation data."""
import attr
import sys
if sys.version_info >= (3, 6):
    from enum import Enum, unique, auto
else:
    enum = None


if enum:
    @unique
    class Tags(Enum):
        CLEAN_NAME = auto()
        DELETE = auto()
        SLATE_FRAME = auto()
        NO_HANDLES = auto()
        BURNIN = auto()
        FTRACK_REVIEW = auto()
        REVIEW = auto()
        THUMBNAIL = auto()
        TO_SCANLINE = auto()


@attr.s
class Representation(object):
    """Class handling representation data."""

    name = attr.ib()
    ext = attr.ib()
    files = attr.ib()
    frameStart = attr.ib()
    frameEnd = attr.ib()
    stagingDir = attr.ib()
    fps = attr.ib(default=None)
    tags = attr.ib(default=attr.Factory(set))

    _id = attr.ib(default=None)


    def __init__(self):
        ...


