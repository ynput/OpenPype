#!/usr/bin/env python
# TODO: convert this script to be usable with PYPE
"""
Example DaVinci Resolve script:
Load a still from DRX file, apply the still to all clips in all timelines.
Set render format and codec, add render jobs for all timelines, render
to specified path and wait for rendering completion.
Once render is complete, delete all jobs
"""
# clonned from: https://github.com/survos/transcribe/blob/fe3cf51eb95b82dabcf21fbe5f89bfb3d8bb6ce2/python/3_grade_and_render_all_timelines.py  # noqa

from python_get_resolve import GetResolve
import sys
import time


def AddTimelineToRender(project, timeline, presetName,
                        targetDirectory, renderFormat, renderCodec):
    project.SetCurrentTimeline(timeline)
    project.LoadRenderPreset(presetName)

    if not project.SetCurrentRenderFormatAndCodec(renderFormat, renderCodec):
        return False

    project.SetRenderSettings(
        {"SelectAllFrames": 1, "TargetDir": targetDirectory})
    return project.AddRenderJob()


def RenderAllTimelines(resolve, presetName, targetDirectory,
                       renderFormat, renderCodec):
    projectManager = resolve.GetProjectManager()
    project = projectManager.GetCurrentProject()
    if not project:
        return False

    resolve.OpenPage("Deliver")
    timelineCount = project.GetTimelineCount()

    for index in range(0, int(timelineCount)):
        if not AddTimelineToRender(
                project,
                project.GetTimelineByIndex(index + 1),
                presetName,
                targetDirectory,
                renderFormat,
                renderCodec):
            return False
    return project.StartRendering()


def IsRenderingInProgress(resolve):
    projectManager = resolve.GetProjectManager()
    project = projectManager.GetCurrentProject()
    if not project:
        return False

    return project.IsRenderingInProgress()


def WaitForRenderingCompletion(resolve):
    while IsRenderingInProgress(resolve):
        time.sleep(1)
    return


def ApplyDRXToAllTimelineClips(timeline, path, gradeMode=0):
    trackCount = timeline.GetTrackCount("video")

    clips = {}
    for index in range(1, int(trackCount) + 1):
        clips.update(timeline.GetItemsInTrack("video", index))
    return timeline.ApplyGradeFromDRX(path, int(gradeMode), clips)


def ApplyDRXToAllTimelines(resolve, path, gradeMode=0):
    projectManager = resolve.GetProjectManager()
    project = projectManager.GetCurrentProject()
    if not project:
        return False
    timelineCount = project.GetTimelineCount()

    for index in range(0, int(timelineCount)):
        timeline = project.GetTimelineByIndex(index + 1)
        project.SetCurrentTimeline(timeline)
        if not ApplyDRXToAllTimelineClips(timeline, path, gradeMode):
            return False
    return True


def DeleteAllRenderJobs(resolve):
    projectManager = resolve.GetProjectManager()
    project = projectManager.GetCurrentProject()
    project.DeleteAllRenderJobs()
    return


# Inputs:
# - DRX file to import grade still and apply it for clips
# - grade mode (0, 1 or 2)
# - preset name for rendering
# - render path
# - render format
# - render codec
if len(sys.argv) < 7:
    print(
        "input parameters for scripts are [drx file path] [grade mode] "
        "[render preset name] [render path] [render format] [render codec]")
    sys.exit()

drxPath = sys.argv[1]
gradeMode = sys.argv[2]
renderPresetName = sys.argv[3]
renderPath = sys.argv[4]
renderFormat = sys.argv[5]
renderCodec = sys.argv[6]

# Get currently open project
resolve = GetResolve()

if not ApplyDRXToAllTimelines(resolve, drxPath, gradeMode):
    print("Unable to apply a still from drx file to all timelines")
    sys.exit()

if not RenderAllTimelines(resolve, renderPresetName, renderPath,
                          renderFormat, renderCodec):
    print("Unable to set all timelines for rendering")
    sys.exit()

WaitForRenderingCompletion(resolve)

DeleteAllRenderJobs(resolve)

print("Rendering is completed.")
