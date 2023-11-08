# -*- coding: utf-8 -*-
"""Extract project for Nuke.

Because original extractor script is intermingled with UI, we had to rewrite
it to be able to call it directly from Python without user interaction.

Because the way it was written, we've changed it a little bit to be more
Pythonic so the way nuke script is generated is a little bit different and
some variables are named slightly different but the logic should be the same.

TODO: This can be refactored even better, split to multiple methods, etc.

"""

from math import pi
from pathlib import Path

import pyblish.api
import tde4  # noqa: F401
from vl_sdv import (rot3d, mat3d, VL_APPLY_ZXY)  # noqa: F401

from openpype.pipeline import KnownPublishError, OptionalPyblishPluginMixin
from openpype.pipeline import publish


def sanitize_name(name: str) -> str:
    """Sanitize name for Nuke."""

    name = name.replace(" ", "_")
    return name.replace("#", "_")


def convert_to_angles(r3d):
    rot = rot3d(mat3d(r3d)).angles(VL_APPLY_ZXY)
    rx = (rot[0] * 180.0) / pi
    ry = (rot[1] * 180.0) / pi
    rz = (rot[2] * 180.0) / pi
    return rx, ry, rz


def convert_zup(p3d, yup):
    return p3d if yup == 1 else [p3d[0], -p3d[2], p3d[1]]


def angle_mod360(d0, d):
    dd = d - d0
    if dd > 180.0:
        d = angle_mod360(d0, d - 360.0)
    elif dd < -180.0:
        d = angle_mod360(d0, d + 360.0)
    return d


class ExtractMatchmoveScriptNuke(publish.Extractor,
                                 OptionalPyblishPluginMixin):
    """Extract Nuke script for matchmove.

    Unfortunately built-in export script from 3DEqualizer is bound to its UI,
    and it is not possible to call it directly from python. Therefore, this
    method is using custom script that is trying to mimic the export script
    as much as possible.

    TODO: Utilize attributes defined in ExtractScriptBase
    """

    label = "Extract Nuke Script"
    families = ["matchmove"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder

    def process(self, instance: pyblish.api.Instance):

        if not self.is_active(instance.data):
            return

        # get camera point group
        point_groups = tde4.getPGroupList()
        for pg in point_groups:
            if tde4.getPGroupType(pg) == "CAMERA":
                point_group = pg
                break
        else:
            # this should never happen as it should be handled by validator
            raise RuntimeError("No camera point group found.")

        cam = tde4.getCurrentCamera()
        img_width = tde4.getCameraImageWidth(cam)
        img_height = tde4.getCameraImageHeight(cam)
        frame0 = tde4.getCameraFrameOffset(cam)
        frame0 -= 1
        frame_count = 0
        last_frame = frame0 + frame_count

        [xa, xb, ya, yb] = tde4.getCameraFOV(cam)

        width = (xb - xa) * img_width
        height = (yb - ya) * img_height

        yup = 1

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
        point_list = tde4.getPointList(point_group)
        pos = 0
        for point in point_list:
            # skip point that are not calculated
            if not tde4.isPointCalculated3D(point_group, point):
                continue

            # TransformGeo Node has 3 inputs, the third is our locator
            # mesh so push NULL twice on the stack and then our
            # geometry reference

            script += '''
push 0
push 0
push $LOCATORREFNODE
'''
            name = tde4.getPointName(point_group, point)
            name = f"p{sanitize_name(name)}"
            p3d = tde4.getPointCalcPosition3D(point_group, point)
            p3d = convert_zup(p3d, yup)

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

        # Merge all the geometry to one geo node using the last
        # "number of point" stack entries
        script += f'''
MergeGeo {{
    inputs {tde4.getNoPoints(point_group)}
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
        no_frames = tde4.getCameraNoFrames(cam)
        point_group_list = tde4.getPGroupList()
        if not point_group_list:
            raise KnownPublishError("Cannot find any point groups.")

        group_xpos = 180

        # write Object Point groups
        pointgroup_name = None
        for pg in point_group_list:
            pointgroup_name = sanitize_name(tde4.getPGroupName(pg))
            pointgroup_name.replace("#", "no")
            if tde4.getPGroupType(pg) != "OBJECT" and cam is None:
                continue

            script += f'''
Group {{
    inputs 0
    name {pointgroup_name}
    xpos {group_xpos}
    groupxpos += 130
    ypos -154
}}

Constant {{
    inputs 0
    color {{0 1 0 1}}
    format "{width} {height} 0 0 {width} {height} 1 {width}_{height}"
    xpos 0
    ypos -442
}}

Sphere {{
    rows 9
    columns 9
    radius 2
    xpos 0
    ypos -346
}}

set OBJECTREF_{pointgroup_name} [stack 0]

push 0
push 0
Axis {{
    rot_order ZXY
'''
            # create curves
            xtrans = "{curve i "
            ytrans = xtrans
            ztrans = xtrans
            xrot = xtrans
            yrot = xtrans
            zrot = xtrans

            frame = 1
            while frame <= no_frames:
                # rot/pos...
                p3d = tde4.getPGroupPosition3D(pg, cam, frame)
                p3d = convert_zup(p3d, yup)
                r3d = tde4.getPGroupRotation3D(pg, cam, frame)
                rot = convert_to_angles(r3d)
                rot0 = rot
                if frame > 1:
                    rot = [angle_mod360(rot0[0], rot[0]),
                           angle_mod360(rot0[1], rot[1]),
                           angle_mod360(rot0[2], rot[2])]
                xtrans = "%s x%d %.15f" % (xtrans, frame + frame0, p3d[0])
                ytrans = "%s x%d %.15f" % (ytrans, frame + frame0, p3d[1])
                ztrans = "%s x%d %.15f" % (ztrans, frame + frame0, p3d[2])
                xrot = "%s x%d %.15f" % (xrot, frame + frame0, rot[0])
                yrot = "%s x%d %.15f" % (yrot, frame + frame0, rot[1])
                zrot = "%s x%d %.15f" % (zrot, frame + frame0, rot[2])

                frame += 1

            scl = tde4.getPGroupScale3D(pg)
            script += f'''
translate {{{xtrans}}} {ytrans}}} {ztrans}}} }}
rotate {{{xrot}}} {yrot}}} {zrot}}} }}
scaling {{{scl:.15f} {scl:.15f} {scl:.15f}}}
    name Axis{pointgroup_name}
    xpos 110
    ypos -366
}}
set Axis{pointgroup_name} [stack 0]
'''
            xpos = 0
            point_list = tde4.getPointList(pg)
            point_count = 0
            for point in point_list:
                if not tde4.isPointCalculated3D(pg, point):
                    continue
                pname = tde4.getPointName(pg, point)
                pname = f"p{sanitize_name(pname)}"
                p3d = tde4.getPointCalcPosition3D(pg, point)
                p3d = convert_zup(p3d, yup)

                script += f'''
push 0
push $Axis{pointgroup_name}
push $OBJECTREF_{pointgroup_name}
"TransformGeo {{
    inputs 3
    translate {{{p3d[0]:.15f} {p3d[1]:.15f} {p3d[2]:.15f}}}
    name {pname}
    xpos {xpos}
    ypos -250
}}
'''
                xpos += 100
                point_count += 1

            script += f'''
MergeGeo {{
    inputs {point_count}
    xpos 0
    ypos -154
}}
Output {{
    xpos 0
    ypos -60
}}
end_group
set GROUP_{pointgroup_name} [stack 0]
'''
        ins = tde4.getNoPGroups()
        script += "push $LOCATOR\n"
        for pg in point_group_list:
            pointgroup_name = sanitize_name(tde4.getPGroupName(pg))
            if tde4.getPGroupType(pg) == "OBJECT" and cam is not None:
                script += f"push $GROUP_{pointgroup_name}\n"

        script += f'''
Scene {{
    inputs {ins}
    name Scene3DE
    xpos 0
    ypos 100
}}
'''
        scene_trs = tde4.getScenePosition3D()
        scene_rot = tde4.getSceneRotation3D()
        r3d = convert_to_angles(scene_rot)
        scl = tde4.getSceneScale3D()
        scene_rot = r3d

        script += f'''
TransformGeo {{
    inputs {ins}
    rot_order ZXY

    translate {{ {scene_trs[0]:.15f} {scene_trs[1]:.15f} {scene_trs[2]:.15f} }}
    rotate {{ {r3d[0]:.15f} {r3d[1]:.15f} {r3d[2]:.15f} }}
    scaling {{ {scl:.15f} {scl:.15f} {scl:.15f} }}"

    name SceneNodeTrans
    xpos 0
    ypos 250
}}
set SCENE3D [stack 0]
'''
        cl = tde4.getCameraList()
        posx = 200
        for cam1 in cl:
            # create Camera Node - the camera has no inputs thus we have
            # to push void onto the stack
            script += f'''
push 0
Axis {{
    inputs 0
    rot_order ZXY

    translate {{ {scene_trs[0]:.15f} {scene_trs[1]:.15f} {scene_trs[2]:.15f} }}
    rotate {{ {scene_rot[0]:.15f} {scene_rot[1]:.15f} {scene_rot[2]:.15f} }}
    scaling {{ {scl:.15f} {scl:.15f} {scl:.15f} }}"
    name Axis{pointgroup_name}
    xpos {posx}
    ypos 100
}}
'''
            no_frames = tde4.getCameraNoFrames(cam1)
            lens = tde4.getCameraLens(cam1)
            img_width = tde4.getCameraImageWidth(cam1)
            img_height = tde4.getCameraImageHeight(cam1)
            camera_name = tde4.getCameraName(cam1)
            filmback_width = tde4.getLensFBackWidth(lens)
            filmback_height = tde4.getLensFBackHeight(lens)

            lco_x = -tde4.getLensLensCenterX(lens) * 2 / filmback_width
            lco_y = -tde4.getLensLensCenterY(lens) * 2 / filmback_width

            [xa, xb, ya, yb] = tde4.getCameraFOV(cam1)

            script += "Camera {\n"
            script += "    rot_order ZXY\n"
            script += "    translate {{curve i "
            frame = 1
            while frame <= no_frames:
                p3d = tde4.getPGroupPosition3D(point_group, cam1, frame)
                p3d = convert_zup(p3d, yup)
                script += "x%d %.15f" % (frame + frame0, p3d[0])
                frame += 1
            script += "} {curve i "

            frame = 1
            while frame <= no_frames:
                p3d = tde4.getPGroupPosition3D(point_group, cam1, frame)
                p3d = convert_zup(p3d, yup)
                script += "x%d %.15f" % (frame + frame0, p3d[1])
                frame += 1
            script += "} {curve i "
            frame = 1
            while frame <= no_frames:
                p3d = tde4.getPGroupPosition3D(point_group, cam1, frame)
                p3d = convert_zup(p3d, yup)
                script += "x%d %.15f" % (frame + frame0, p3d[2])
                frame += 1
            script += "} }\n"

            script += "rotate {{curve i "
            frame = 1
            while frame <= no_frames:
                r3d = tde4.getPGroupRotation3D(point_group, cam1, frame)
                rot = convert_to_angles(r3d)
                rot0 = rot
                if frame > 1:
                    rot = [angle_mod360(rot0[0], rot[0]),
                           angle_mod360(rot0[1], rot[1]),
                           angle_mod360(rot0[2], rot[2])]
                script += "x%d %.15f" % (frame + frame0, rot[0])
                frame += 1
            script += "} {curve i "
            frame = 1
            while frame <= no_frames:
                r3d = tde4.getPGroupRotation3D(point_group, cam1, frame)
                rot = convert_to_angles(r3d)
                rot0 = rot
                if frame > 1:
                    rot = [angle_mod360(rot0[0], rot[0]),
                           angle_mod360(rot0[1], rot[1]),
                           angle_mod360(rot0[2], rot[2])]
                script += "x%d %.15f" % (frame + frame0, rot[1])
                frame += 1
            script += "} {curve i "
            frame = 1
            while frame <= no_frames:
                r3d = tde4.getPGroupRotation3D(point_group, cam1, frame)
                rot = convert_to_angles(r3d)
                rot0 = rot
                if frame > 1:
                    rot = [angle_mod360(rot0[0], rot[0]),
                           angle_mod360(rot0[1], rot[1]),
                           angle_mod360(rot0[2], rot[2])]
                script += "x%d %.15f" % (frame + frame0, rot[2])
                frame += 1
            script += " }}\n"

            script += "focal {{ i"
            frame = 1
            while frame <= no_frames:
                focal = tde4.getCameraFocalLength(cam1, frame) * 10
                script += " x%d %.15f" % (frame + frame0, focal)
                frame += 1
            script += " }}\n"

            script += f'''
    haperture {filmback_width * 10:.15f}
    vaperture {filmback_height * 10:.15f}
    win_translate {{ {lco_x:.15f} {lco_y:.15f} }}

    win_scale {{1 1}}
    name {camera_name}1
    xpos {posx}
    ypos 200
}}

push $SCENE3D
'''

            if xa == 0 and xb == 1.0 and ya == 0 and yb == 1:
                script += "push 0\n"
            else:
                script += f'''
Crop {{
    inputs 0
    box {{ {xa * img_width} {ya * img_height} {xb * img_width} {yb * img_height} }}
    reformat true
    crop false
    name Crop1
    xpos 0
    ypos 200
}}
'''
            script += f'''
ScanlineRender {{
    inputs 3
    name render3DE({camera_name})
    xpos {posx}
    ypos 300
}}
'''
            posx += 175

        # do the extraction itself
        staging_dir = self.staging_dir(instance)
        file_path = Path(staging_dir) / "nuke_export.nk"
        with open(file_path, "w") as f:
            f.write(script)

        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': "nk",
            'ext': "nk",
            'files': file_path.name,
            "stagingDir": staging_dir,
        }
        self.log.debug(f"output: {file_path.as_posix()}")
        instance.data["representations"].append(representation)
