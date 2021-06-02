# -*- coding: utf-8 -*-
"""Class for handling representation data."""
import attr


@attr.s
class Representation(object):
    """Class handling representation data."""

    name = attr.ib()
    ext = attr.ib()
    files = attr.ib()
    frameStart = attr.ib()
    frameEnd = attr.ib()
    stagingDir = attr.ib()
    fps = attr.ib()
    tags = attr.ib()

    _id = attr.ib(default=None)

    def __init__(self):
        ...


