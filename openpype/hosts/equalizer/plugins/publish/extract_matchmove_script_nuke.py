# -*- coding: utf-8 -*-
"""Extract project for Nuke"""

import contextlib
from pathlib import Path

import pyblish.api
import tde4

from openpype.hosts.equalizer.api import (
    ExtractScriptBase,
    maintained_model_selection,
)


def sanitize_name(name: str) -> str:
    """Sanitize name for Nuke."""

    name = name.replace(" ", "_")
    return name.replace("#", "_")


class ExtractMatchmoveScriptNuke(ExtractScriptBase):
    """Extract Nuke script for matchmove.

    Unfortunately built-in export script from 3DEqualizer is bound to its UI,
    and it is not possible to call it directly from python. Therefore, this
    method is using custom script that is trying to mimic the export script
    as much as possible.
    """

    label = "Extract Nuke Script"
    families = ["matchmove"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder

    def process(self, instance: pyblish.api.Instance):
        frame0 = 0
        frame_count = 0
        last_frame = frame0 + frame_count

        width = 0
        height = 0

        script = f'''
#! nuke4.8 -nx
version 4.8200

# write root properties
Root {{
    inputs 0
    name 3DE_Export_Root
    frame {frame0}
    last_frame {last_frame}
    format "{width} {height} 0 0 {width} {height} 1 {width}_{height}"
}}

# Create Locator Group
Group {{
    inputs 0
    name Locators
    xpos 0
    ypos 0
}}

Constant {{
    inputs 0
    color {{1 0 0 1}}
    format "{width} {height} 0 0 {width} {height} 1 {width}_{height}"
    xpos 0
    ypos -442
}}

# Create reference geometry node
Sphere {{
    rows 9
    columns 9
    radius 2
    xpos 0
    ypos -346
}}

# assign a variable name to it - needed for pushing it on the top of the
stack later
set LOCATORREFNODE [stack 0]
        '''

        # Create the locators
        point_list = tde4.getPointList(campg)
        pos = 0
        for point in point_list:
            # skip point that are not calculated
            if not tde4.isPointCalculated3D(campg, point):
                continue

            # TransformGeo Node has 3 inputs, the third is our locator
            # mesh so push NULL twice on the stack and then our
            # geometry reference

            script += '''
push 0
push 0
push $LOCATORREFNODE
'''
            name = tde4.getPointName(campg, point)
            name = f"p{sanitize_name(name)}"
            p3d = tde4.getPointCalcPosition3D(campg, point)
            p3d = convertZup(p3d, yup)

            script += f'''
TransformGeo {{
    inputs 3
    translate {{{p3d[0]:.15f} {p3d[1]:.15f} {p3d[2]:.15f}}}
    name {name}
    xpos {pos}
    pos += 100
    ypos -250
}}
'''
            pos += 100
        script += f'''
# Merge all the geometry to one geo node using the last "number of point" stack entries
MergeGeo {{
    inputs {tde4.getNoPoints(campg)}
    xpos 0
    ypos -154
}}

Output {{
    xpos 0
    ypos -60
}}
# finish locator group
end_group
set LOCATOR [stack 0]
'''
        noframes = tde4.getCameraNoFrames(cam)
        pgl = tde4.getPGroupList()
        index = 1
        groupxpos = 180
