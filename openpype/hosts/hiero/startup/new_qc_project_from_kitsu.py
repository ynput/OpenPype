""" OpenPype custom script for resetting read nodes start frame values """
import os
import re
import re
import pprint
import distutils.dir_util

import hiero.core
import hiero.ui
from hiero.core import (newProject, BinItem, Bin, Sequence, VideoTrack)
import foundry.ui

from bson import json_util
from datetime import date, datetime
import gazu

from openpype.modules.kitsu.utils import credentials
from openpype.client import get_representations

from qtpy import QtWidgets
from qtpy.QtWidgets import QInputDialog, QLineEdit

from openpype.lib import Logger
log = Logger.get_logger(__name__)

def main():
    print("Loaded script 'new_qc_project_from_kitsu.py'")

    playlist_url, ok = QInputDialog().getText(None, "New QC Project Playlist",
                                        "Playlist URL:", QLineEdit.Normal)

    create_qc_timeline(playlist_url)

# def create_project():
#     project = hiero.core.newProject()

#     project_path = os.path.join(
#         hiero.plugins.hsutils.get_project_path(), "edit", "qc")

#     job_name = os.environ["JOB"]
#     project_version = 1

#     """
#     create directory if doesn't exist
#     search for latest project version number if exists
#     """
#     if not os.path.exists(project_path):
#         distutils.dir_util.mkpath(project_path)
#     else:
#         projects = [project for project in os.listdir(
#             project_path) if ".hrox" in project]
#         projects = sorted(
#             projects, key=lambda project: getVersionNumberFromText(project), reverse=True)

#         if projects:
#             project_version = getVersionNumberFromText(projects[0]) + 1

#     project_name = "{}_qc_v{}.hrox".format(job_name, project_version)

#     project.saveAs(os.path.join(project_path, project_name))

#     return project

# ------------------------------------------
# UTILITY FUNCTIONS - EXTRACT ID FROM URL
# ------------------------------------------
# def getVersionNumberFromText(text):
#     """
#     Searching for _v#
#     Return #
#     """
#     match = re.match(r".*_v([0-9]+).*", text)

#     if match:
#         return int(match.group(1))
#     else:
#         return None


# def createClipFromVersion(version):
#     frame_first = version.frame_first
#     frame_last = version.frame_last
#     fps = version.project.fps
#     clip = None

#     # Path to Frames from Tracker
#     path_to_frames = version._path_to_frames
#     if os.path.exists(os.path.dirname(version._path_to_frames)):
#         if len(os.listdir(os.path.dirname(version._path_to_frames))) > 0:
#             clip = hiero.core.Clip(version._path_to_frames)
#             clip.setName("{}@{}".format(version.name, version.link.name))
#             return clip

#     # Computed Path To Frames
#     path_to_frames = version.get_path_to_frames(absolute=True)
#     if os.path.exists(os.path.dirname(path_to_frames)):
#         if len(os.listdir(os.path.dirname(path_to_frames))) > 0:
#             clip = hiero.core.Clip(path_to_frames)
#             clip.setName("{}@{}".format(version.name, version.link.name))
#             return clip

#     # Offline Media
#     if frame_first and frame_last and fps:
#         media_source = hiero.core.MediaSource().createOfflineVideoMediaSource(
#             version._path_to_frames, frame_first, frame_last - frame_first + 1, fps)

#         clip = hiero.core.Clip(media_source)
#         clip.setName("{}@{}".format(version.name, version.link.name))

#         return clip


# helper method for creating track items from clips
# def createTrackItem(track, trackItemName, sourceClip, lastTrackItem=None):
#     # create the track item
#     trackItem = track.createTrackItem(trackItemName)

#     # set it's source
#     trackItem.setSource(sourceClip)

#     # set it's timeline in and timeline out values, offseting by the track item before if need be
#     if lastTrackItem:
#         trackItem.setTimelineIn(lastTrackItem.timelineOut() + 1)
#         trackItem.setTimelineOut(
#             lastTrackItem.timelineOut() + sourceClip.duration())
#     else:
#         trackItem.setTimelineIn(0)
#         trackItem.setTimelineOut(trackItem.sourceDuration() - 1)

#     # add the item to the track
#     track.addItem(trackItem)
#     return trackItem



def list_files(path):
    files_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            files_list.append(os.path.join(root, file))
        for dir in dirs:
            list_files(os.path.join(root, dir))
    return files_list


def create_qc_timeline(playlist_url):

    user, password = credentials.load_credentials()

    if credentials.validate_credentials(user, password):
        # URL has the playlist id that we need to locate the playlist
        pattern = r"playlists\/([^\/]+)"
        results = re.search(pattern, playlist_url)

        playlist_id = None
        if len(results.groups()) > 0:
            playlist_id = results.group(1)
            log.info(f"Playlist ID: {playlist_id}")

            gazu.log_in(user, password)

            playlist = gazu.playlist.get_playlist(playlist_id)
            playlist_name = playlist.get("name")

            # Get current project and clipbin:
            myProject = hiero.core.projects()[-1]
            clipsBin = myProject.clipsBin()

            qc_bin = hiero.core.Bin("QC_{}".format(playlist_name))
            clipsBin.addItem(qc_bin)

            sequence = hiero.core.Sequence(playlist_name)
            clipsBin.addItem(hiero.core.BinItem(sequence))

            videotrack = hiero.core.VideoTrack("latest compo")
            audiotrack = hiero.core.AudioTrack("animatic")

            # Set initial position in timeline
            timeline_in = 0

            log.info(f"Processing {playlist_name}")

            for entity in playlist.get("shots"):
                # Get id's
                entity_id = entity.get("entity_id")
                preview_file_id = entity.get("preview_file_id")

                # Get shot, preview and task
                shot = gazu.shot.get_shot(entity_id)
                preview_file = gazu.files.get_preview_file(preview_file_id)
                task_id = preview_file["task_id"]
                task = gazu.task.get_task(task_id)

                #####################
                # Compositing plates:
                # Get representations and place them in video track

                compo_representations = get_plate_representations("compo", shot, task, preview_file)

                frame_in = None
                # Of all representations, we keep the 'png', just first and last frame
                for repr in compo_representations:
                    if repr["name"] == "png":
                        frame_in = repr["files"][0]
                        frame_out = repr["files"][-1]
                        log.info(repr["files"][0])
                        break

                if frame_in:
                    path_to_representation = frame_in["path"].replace("\\", "/")
                    path_to_representation = path_to_representation.replace("{root[work]}", "Y:/WORKS/_openpype")
                    add_track_item(path_to_representation, qc_bin, videotrack, timeline_in)

                #####################
                # Animatic plates:
                # Get representations and place them in audio track

                animatic_representations = get_plate_representations("animatic", shot)

                # Get the latest version of animatic
                max_index = 0
                newest_version = None
                for repr in animatic_representations:
                    if int(repr["context"]["version"]) >= max_index:
                        max_index = int(repr["context"]["version"])
                        newest_version = repr

                animatic_path = newest_version["data"]["path"].replace("\\", "/")

                source_duration = add_track_item(animatic_path, qc_bin, audiotrack, timeline_in)

                # Move the position in timeline
                timeline_in += source_duration + 5

            # Add tracks to sequence and display it
            sequence.addTrack(audiotrack)
            sequence.addTrack(videotrack)
            editor = hiero.ui.getTimelineEditor(sequence)
            editor.window()


def add_track_item(path_to_representation, bin, track, timeline_in):
    repr_clip = bin.createClip(path_to_representation)
    trackItem = track.createTrackItem(path_to_representation)
    trackItem.setSource(repr_clip)
    trackItem.setTimelineIn(timeline_in)
    trackItem.setTimelineOut(timeline_in + trackItem.sourceDuration() + 1)
    trackItem.setPlaybackSpeed(1)
    track.addItem(trackItem)
    log.info("Added track item and uptated timeline_in to {}".format(timeline_in))

    # Return the duration of clip
    return trackItem.sourceDuration()


def get_plate_representations(plate_type, shot, task=None, preview_file=None):
    context = {
        "project_name": shot["project_name"],
        "asset_name": shot["name"]
    }
    context_filters = {
        "asset": context["asset_name"]
    }

    if plate_type == "compo" and task and preview_file:
        # TODO: This is pretty hacky we are retrieving the
        # Avalon Version number from the original name of
        # the file uploaded to Kitsu. I couldn't find
        # any way to relate Kitsu Preview Files to OP Representations.
        log.info("Getting representations of compos")
        log.info(preview_file["original_name"])

        version_regex = re.compile(r"^.+_v([0-9]+).*$")
        regex_result = version_regex.findall(preview_file["original_name"])
        representation_version_number = int(regex_result[0])

        context["task_name"] = task["task_type"]["name"]
        context_filters["version"] = representation_version_number
        context_filters["task"] = {"name": context["task_name"]}

        representations = get_representations(context["project_name"],
                                                      context_filters=context_filters)

    elif plate_type == "animatic":
        log.info("Getting representations of animatics")

        context["task_name"] = "Edit"
        context_filters["subset"] = ["plateAnimatic"]
        context_filters["representation"] = ["mp4"]

        representations = get_representations(context["project_name"],
                                                      context_filters=context_filters)

    else:
        raise RuntimeError("No valid plate type")

    return representations
