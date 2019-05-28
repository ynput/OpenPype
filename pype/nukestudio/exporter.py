# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import collections
import os
import re
import math

import time
import datetime
import getpass
import itertools

from hiero.core import ITask

from hiero.core import ITaskPreset
from hiero.core import defaultFrameRates
from hiero.core import ItemWrapper
from hiero.core import ResolveTable
from hiero.core import TrackItem
from hiero.core import MediaSource
from hiero.core import Clip
from hiero.core import Sequence
from hiero.core import ApplicationSettings
from hiero.core import isVideoFileExtension
from hiero.core import Keys
from hiero.core import ResolveTable
from hiero.core import log
from hiero.core import VideoTrack
from hiero.core import AudioTrack
from hiero.core import Transition
from hiero.core import remapPath
from hiero.core import util
from . FnCompSourceInfo import CompSourceInfo
from FnFloatRange import *
from collections import OrderedDict
import types
import sys


# Given a type, return a string representation stripped of unnecessary characters
def classBasename(objecttype):
    # <class 'hiero.exporters.FnNukeShotExporter.NukeShotPreset'>
    typename = str(objecttype)
    result = re.match(r"<(class|type) \'(?P<name>[\w\.]+)\'>", typename)
    if result:
        return result.group("name")
    else:
        return typename


class TaskData(dict):
    """TaskData is used as a seed for creating classes, wrapping up all of
    the parameters and making it simpler to add new ones"""

    kPreset = "preset"
    kItem = "item"
    kExportRoot = "exportRoot"
    kShotPath = "shotPath"
    kVersion = "version"
    kExportTemplate = "exportTemplate"
    kResolver = "resolver"
    kCutHandles = "cutHandles"
    kRetime = "retime"
    # Parameter indicating where the start frame should be taken from.  Current possible values are Source, Sequence and Custom
    kStartFrameSource = "startFrameSource"
    kStartFrame = "startFrame"
    kProject = "project"
    kSubmission = "submission"
    kSkipOffline = "skipOffline"
    kPresetId = "presetId"
    kShotNameIndex = "shotNameIndex"
    kMediaToSkip = "mediaToSkip"

    def __init__(self,
                 preset,
                 item,
                 exportRoot,
                 shotPath,
                 version,
                 exportTemplate,
                 project,
                 cutHandles=None,
                 resolver=None,
                 retime=False,
                 startFrame=None,
                 startFrameSource=None,
                 submission=None,
                 skipOffline=True,
                 presetId=None,
                 shotNameIndex='',
                 mediaToSkip=[]):
        dict.__init__(self)

        self[TaskData.kPreset] = preset
        self[TaskData.kItem] = item
        self[TaskData.kExportRoot] = exportRoot
        self[TaskData.kShotPath] = shotPath
        self[TaskData.kVersion] = version
        self[TaskData.kExportTemplate] = exportTemplate
        self[TaskData.kCutHandles] = cutHandles
        self[TaskData.kRetime] = retime
        self[TaskData.kStartFrame] = startFrame
        self[TaskData.kStartFrameSource] = startFrameSource
        self[TaskData.kProject] = project
        self[TaskData.kSkipOffline] = skipOffline
        self[TaskData.kPresetId] = presetId
        self[TaskData.kShotNameIndex] = shotNameIndex
        self[TaskData.kMediaToSkip] = mediaToSkip

        if submission is not None:
            self[TaskData.kSubmission] = submission

        if resolver is None:
            if preset:
                self[TaskData.kResolver] = preset.createResolver()
            else:
                self[TaskData.kResolver] = None
        else:
            self[TaskData.kResolver] = resolver.duplicate()
            if preset:
                self[TaskData.kResolver].merge(preset.createResolver())


class TaskCallbacks(object):
    """
    This class manages callback functions that can be called
    when a Task goes into a particular state.
    """
    _callbacks = collections.defaultdict(list)

    # callback types...
    onTaskStart = "onTaskStart"
    onTaskFinish = "onTaskFinish"

    @classmethod
    def addCallback(cls, callbackType, callbackFn):
        """
        Add the given callback function and callbackType.
        The callback will be executed when TaskCallbacks.call
        is called with the same callbackType.
        """
        cls._callbacks[callbackType].append(callbackFn)

    @classmethod
    def call(cls, callbackType, task):
        """
        Call all the callback functions for the given callbackType passing in
        task as the only argument.
        """
        for callbackFn in cls._callbacks[callbackType]:
            callbackFn(task)


class TaskBase(ITask):
    """TaskBase is the base class from which all Tasks must derrive."""

    def __init__(self, initDictionary):
        """__init__(self, initDictionary)
        Initialise TaskBase Class

        @param initDictionary : a TaskData dictionary which seeds the task with all initialization data
        """

        ITask.__init__(self)

        preset = initDictionary[TaskData.kPreset]
        self._presetId = initDictionary[TaskData.kPresetId]
        item = initDictionary[TaskData.kItem]
        exportRoot = initDictionary[TaskData.kExportRoot]
        shotPath = initDictionary[TaskData.kShotPath]
        version = initDictionary[TaskData.kVersion]
        exportTemplate = initDictionary[TaskData.kExportTemplate]

        # The number of frames of handles to be included when exporting a track
        # item.  If this is None, it means the full clip length should be exported.
        self._cutHandles = initDictionary[TaskData.kCutHandles]

        self._resolver = initDictionary[TaskData.kResolver]
        self._retime = initDictionary[TaskData.kRetime]
        self._startFrame = initDictionary[TaskData.kStartFrame]
        self._startFrameSource = initDictionary[TaskData.kStartFrameSource]
        self._shotNameIndex = initDictionary[TaskData.kShotNameIndex]

        self._skipOffline = True
        if TaskData.kSkipOffline in initDictionary:
            self._skipOffline = initDictionary[TaskData.kSkipOffline]

        self._mediaToSkip = initDictionary[TaskData.kMediaToSkip]

        self._submission = None
        if TaskData.kSubmission in initDictionary:
            self._submission = initDictionary[TaskData.kSubmission]

        self._projectName, self._projectRoot, self._projectSettings = "", "", None
        self._project = initDictionary[TaskData.kProject]
        if self._project is not None:
            self._projectName = self._project.name()
            self._projectRoot = self._project.exportRootDirectory()
            try:
                self._projectSettings = self._project.extractSettings()
            except Exception as e:
                # may throw an exception if project setting is invalid
                self.setError(str(e))

        # Grab timestamp at time of creation. Primarily used for resolving date tokens.
        self._timeStamp = datetime.datetime.now()

        self._sequence = None
        self._track = None
        self._trackitem = None
        self._clip = None
        self._source = None
        self._fileinfo = None
        self._exportTemplate = exportTemplate
        self._item = item
        self._filename = None
        self._filebase = None
        self._fileext = None
        if isinstance(version, basestring):
            self._versionString = version
        else:
            self._versionString = "v%02d" % version

        if isinstance(item, (TrackItem, Clip)):
            # If these fail, the object is badly formed -- it has no internal C++ object.
            assert item, "Null Item."
            if isinstance(item, TrackItem):
                self._clip = item.source()
                self._track = item.parent()
                assert self._track, "Null Parent Track"
                self._sequence = self._track.parent()
                assert self._sequence, "Null Sequence"
            else:
                self._clip = item

            assert self._clip, "Null clip."
            assert isinstance(
                self._clip, Clip), "Track item does not contain a source clip."
            self._source = self._clip.mediaSource()
            assert self._source, "Null source."

            # Get the filepath info from the clip. Currently we only allow one but when more
            # are permitted in the future (eg stereo clips) this will need updating.
            self._fileinfo = self._source.fileinfos()[0]
            filename = self._fileinfo.filename()
            if filename is not None and len(filename) > 0:
                self._filename = os.path.basename(filename)
                self._filebase, self._fileext = os.path.splitext(
                    self._filename)

            # Remove fragment index from r3d files B007_C006_0321VN_002.R3D (_002 is usually hidden from the user)
            if self._fileext is not None and self._fileext.lower() == ".r3d":
                self._filebase = self._filebase[:16]
                self._filename = self._filebase + self._fileext

        elif isinstance(item, Sequence):
            self._sequence = item
            assert self._sequence, "Null Sequence"

        self._item = item
        self._preset = preset
        self._exportRoot = exportRoot.replace("\\", "/")
        self._shotPath = shotPath.replace("\\", "/")
        self._version = version

        self._exportPath = os.path.join(self._exportRoot, self._shotPath)

        desc = self.ident().rsplit('.', 1)[1]
        self.setFormatDescription(desc)
        self.setDestinationDescription(
            os.path.dirname(self.resolvedExportPath()))

        self._finished = False

    def timeStampString(self, localtime):
        """timeStampString(localtime)
           Convert a tuple or struct_time representing a time as returned by gmtime() or localtime() to a string formated YEAR/MONTH/DAY TIME."""
        return time.strftime("%Y/%m/%d %X", localtime)

    def setError(self, desc):
        """setError(self, desc) Call to set the state of this task to error, with a description of the error.
           If the task is synchronous, raise exception"""
        ITask.setError(self, desc)
        if self.synchronous():
            raise Exception, desc

    def validate(self):
        """ Check that the task is in a state that allows it to be executed. Should
        raise an exception if there is an error. The default implementation does
        nothing.
        """
        pass

    def updateItem(self, originalItem, localtime):
        """updateItem - This is called by the processor prior to taskStart, crucially on the main thread.\n
          This gives the task an opportunity to modify the original item on the main thread, rather than the clone."""
        pass

    def timeStamp(self):
        """timeStamp(self)
        Returns the datetime object from time of task creation"""
        return self._timeStamp

    def fileName(self):
        """filename(self)
        Returns the source items filename if applicable"""
        return self._filename

    def fileext(self):
        """fileext(self)
        Returns the source items file extention if applicable"""
        return (self._fileext[1:] if self._fileext else "")

    def filebase(self):
        """filebase(self)
        Returns the source items file path less extension if applicable"""
        return self._filebase

    def filehead(self):
        """filehead(self)
        Returns the source filename excluding image sequence frame padding and extension, if applicable"""
        if self._source:
            return mediaSourceExportFileHead(self._source)
        return self._filebase

    def filepath(self):
        """filepath(self)
        Returns the source file path, if applicable"""
        if self._source:
            return os.path.dirname(self._source.firstpath())
        return ""

    def filepadding(self):
        """filepadding(self)
        Returns the padding used in source file if an image sequence, empty string otherwise"""
        if self._source:
            padding = self._source.filenamePadding()
            return "%%0%id" % padding
        return ""

    def shotName(self):
        """shotName(self)
        Returns the Tasks track item name"""
        return self._item.name()

    def clipName(self):
        """clipName(self)
        Returns the name of the clip in the bin"""
        return self._clip.name()

    def trackName(self):
        """trackName(self)
        Returns the name of the parent track"""
        return self._track.name()

    def versionString(self):
        """versionString(self)
        Returns the version string used to resolve the {version} token"""
        return self._versionString

    def sequenceName(self):
        """sequenceName(self)
        Returns the name of the sequence or parent sequence (if exporting a track item)"""
        if self._sequence:
            return self._sequence.name()
        else:
            return ""

    def shotNameIndex(self):
        """ shotNameIndex(self)
        Returns the index string for the shot, if there are multiple shots with the same name on the sequence. """
        return self._shotNameIndex

    def name(self):
        return str(type(self))

    def projectName(self):
        """projectName(self)
        Returns the name of the project, used for resolving the {project} token)"""
        return str(self._projectName)

    def projectRoot(self):
        """projectRoot(self)
        Returns the project root export path, used for resolving the {projectroot} token"""
        return self._projectRoot

    def editId(self):
        """ editId(self)
        Returns a str containing the id of this edit.  See hiero.core.TrackItem.eventNumber(). """
        if (self._item != None) and isinstance(self._item, TrackItem):

            eventId = self._item.eventNumber()
            # When the track items are cloned, a tag is added which tracks the parent object, and contains the eventid
            # Take the event id from the tag because the cloned parent sequence may have been cropped changing the eventids
            eventTag = [tag.metadata().value('tag.event')
                        for tag in self._item.tags() if tag.metadata().hasKey('tag.event')]
            # If a tag has been found containing the event metadata return that value
            if eventTag:
                eventId = int(eventTag[0])

            return str(eventId).rjust(self._editIdPadding(), '0')
        else:
            return "UnknownEditId"

    def _editIdPadding(self):
        """ Get the padding for editId strings, based on the total number of track items in the sequence """
        if not self._sequence:
            return 0
        totalTrackItems = 0
        for track in itertools.chain(self._sequence.videoTracks(), self._sequence.audioTracks()):
            totalTrackItems = totalTrackItems + track.numItems()
        # Use at least 3 digits of padding, or more if there are more than 999 track items
        return max(3, len(str(totalTrackItems)))

    def edlEditId(self):
        """ edlEditId(self)
        Returns the id taken from the EDL used to create this edit, if there was one. """
        if (self._item != None) and isinstance(self._item, TrackItem):
            metadata = self._item.metadata()
            key = "foundry.edl.editNumber"
            if metadata.hasKey(key):
                return metadata.value(key)
        return "UnknownEditId"

    def ident(self):
        """ident(self)
        Returns a string used for identifying the type of export task"""
        return classBasename(type(self))

    def addToQueue(self):
        """addToQueue(self)
        Called by the processor in order to add the Task to the ExportQueue
        If derrived classes impliment this function, this base function must be called.

        Populates name, description and destination fields in the export queue"""

        ITask.addToQueue(self)

        # Set error state if the task is not able to run
        if not self.hasValidItem():
            itemTypeString = "sequence" if (
                self._preset.supportedItems() == TaskPresetBase.kSequence) else "clip"
            self.setError("Task cannot be run, only valid for a %s" %
                          itemTypeString)

    def printState(self):
        """Print summary of the task parameters"""
        print "TaskBase -- task state:"
        print "  - preset:", self._preset
        print "  - sequence:", self._sequence
        if self._trackitem:
            print "  - trackitem:", self._trackitem
            print "  - clip:", self._clip
            print "  - source:", self._source
            print "  - shotPath:", self._shotPath
        print "  - exportRoot:", self._exportRoot
        print "  - version:", self._version
        print "  - exportPath:", self._exportPath
        print " - resolve table: ", str(self._resolver._resolvers)

    def resolvePath(self, path):
        """Replace any recognized tokens in path with their current value."""

        # Replace Windows path separators before token resolve
        path = path.replace("\\", "/")

        try:
            # Resolve token in path
            path = self._resolver.resolve(self, path, isPath=True)
        except RuntimeError as error:
            self.setError(str(error))

        # Strip padding out of single file types
        if isVideoFileExtension(os.path.splitext(path)[1].lower()):
            path = re.sub(r'.[#]+', '', path)
            path = re.sub(r'.%[\d]+d', '', path)

        # Normalise path to use / for separators
        path = path.replace("\\", "/")

        # Strip trailing spaces on directory names.  This causes problems on Windows
        # because it will not let you create a directory ending with a space, so if you do
        # e.g. mkdir("adirectory ") the space will be silently removed.
        path = path.replace(" /", "/")

        return path

    def resolvedExportPath(self):
        """resolvedExportPath()
        returns the output path with and tokens resolved"""
        return self.resolvePath(self._exportPath)

    def _outputHandles(self, ignoreRetimes):
        """ Internal _outputHandles() method.  Should be reimplemented by sub-classes
            rather than outputHandles(). """
        startH, endH = self.inputRange(False, ignoreRetimes)
        start, end = self.inputRange(True, ignoreRetimes)

        return int(start - startH), int(endH - end)

    def outputHandles(self, ignoreRetimes=False):
        """outputHandles( ignoreRetimes = False )
        Return a tuple of the in/out handles generated by this task.
        Handles may be cropped such as to prevent negative frame indexes.
        Note that both handles are positive, i.e. if 12 frames of handles are specified, this will return (12, 12)
        Sub-classes should reimplement _outputHandles() rather than this method.
        @return : (in_handle, out_handle) tuple
        """
        startHandle, endHandle = self._outputHandles(ignoreRetimes)

        if startHandle < 0 or endHandle < 0:
            raise RuntimeError("TaskBase.outputHandles error, values must not be negative %s %s" % (
                startHandle, endHandle))

        return startHandle, endHandle

    def availableOutputHandles(self):
        """ Get the available output handles, based on self._cutHandles.
            If outputting to sequence time, the start handle is clamped to prevent going into negative frames. """
        if self.outputSequenceTime() and isinstance(self._item, TrackItem):
            return min(self._cutHandles, self._item.timelineIn()), self._cutHandles
        else:
            return self._cutHandles, self._cutHandles

    def inputRange(self, ignoreHandles=False, ignoreRetimes=False, clampToSource=True):
        """inputRange()
        Returns the input frame range (as a tuple) for this task if applicable
        @param: ignoreHandles - If True calculate Input Range excluding export handles
        @param: ignoreRetimes - If True calculate Input Range without taking retimes into account
        @param: clampToSource - If True the input range will be clamped to the available media range"""

        log.debug(">>> inputRange()")
        start, end = 0, 0

        if isinstance(self._item, (TrackItem, Clip)):
            if self._cutHandles is None:
                # Exporting the whole clip or soft trims range.
                start = 0
                end = self._clip.duration() - 1
                if self._clip.softTrimsEnabled():
                    start = self._clip.softTrimsInTime()
                    end = self._clip.softTrimsOutTime()
            else:
                # Exporting only the amount cut in handles.
                ti = self._item
                log.debug("  ti.sourceIn() =" + str(ti.sourceIn()))
                log.debug("  ti.sourceOut() =" + str(ti.sourceOut()))
                log.debug("  self._cutHandles =" + str(self._cutHandles))

                # Ensure _start <= _end (for negative retimes, sourceIn > sourceOut)
                sourceInOut = (ti.sourceIn(), ti.sourceOut())
                start = min(sourceInOut)
                end = max(sourceInOut)

                inHandle, outHandle = 0, 0

                # Don't include handles if the clip is a freeze frame
                isFreezeFrame = (
                    ignoreRetimes == False and self._retime and ti.playbackSpeed() == 0.0)

                if ignoreHandles is False and not isFreezeFrame:
                    inHandle, outHandle = self.availableOutputHandles()

                # Add transition Handles
                inTransition, outTransition = ti.inTransition(), ti.outTransition()
                inTransitionHandle, outTransitionHandle = 0, 0
                if outTransition is not None and not outTransition.isNull():
                    if outTransition.alignment() == Transition.kDissolve:
                        # Calculate the delta required to move the end of the clip to cover the disolve transition
                        outTransitionHandle = (
                            outTransition.timelineOut() - ti.timelineOut())
                        outHandle += outTransitionHandle
                        log.debug("  outTransitionHandle = "
                                  + str(outTransitionHandle))
                if inTransition is not None and not inTransition.isNull():
                    if inTransition.alignment() == Transition.kDissolve:
                        # Calculate the delta required to move the begining of the clip to cover the disolve transition
                        inTransitionHandle = (
                            ti.timelineIn() - inTransition.timelineIn())
                        inHandle += inTransitionHandle
                        log.debug("  inTransitionHandle = "
                                  + str(inTransitionHandle))

                log.debug("  ignoreRetimes = %s, self._retime = %s" %
                          (str(ignoreRetimes), str(self._retime)))
                # Compensate for retimes in handle length
                if not ignoreRetimes and self._retime is True:
                    retimeRate = ti.playbackSpeed()
                    inHandle = math.ceil(inHandle * retimeRate)
                    outHandle = math.ceil(outHandle * retimeRate)

                # Apply handles to start/end frame
                start = start - inHandle
                end = end + outHandle

            log.debug("  relative start =" + str(start))
            log.debug("  relative end =" + str(end))

            firstFrameNumber = self._clip.sourceIn()
            lastFrameNumber = self._clip.sourceOut()
            log.debug("  firstFrameNumber =" + str(firstFrameNumber))
            log.debug("  lastFrameNumber =" + str(lastFrameNumber))

            # Offset start and end by offset clip wrapper offset and starting
            # frame number to map into the file frame range.
            start = start + firstFrameNumber
            end = end + firstFrameNumber
            log.debug("  file start =" + str(start))
            log.debug("  file end =" + str(end))

            if clampToSource:
                # Trim back to the available file range.
                start = max(start, firstFrameNumber)
                end = min(end, lastFrameNumber)
            # If not clamping to source, we at least need to make sure the start frame is not negative
            else:
                start = max(start, 0)

        log.debug("  export start =" + str(start))
        log.debug("  export end =" + str(end))

        return (start, end)

    def outputSequenceTime(self):
        """ Test if the output frame range should be in sequence time rather than source. This
            only applies when a TrackItem is being exported.

            NOTE: This option has been disabled for the time being.  The code is left in place in case we want to re-enable it,
            but it is not available to users. """
        return False
        # return (self._startFrameSource == "Sequence")

    def outputRange(self, ignoreHandles=False, ignoreRetimes=False, clampToSource=True):
        """outputRange()
        Returns the output file range (as tuple) for this task, if applicable.
        This default implementation works if the task was initialised with a Clip or TrackItem"""
        start = 0
        end = 0
        if isinstance(self._item, (TrackItem, Clip)):
            # Get input frame range
            start, end = self.inputRange(
                ignoreHandles=ignoreHandles, ignoreRetimes=ignoreRetimes, clampToSource=clampToSource)

            start = int(math.floor(start))
            end = int(math.ceil(end))

            # Offset by custom start time
            if self._startFrame is not None:
                end = self._startFrame + (end - start)
                start = self._startFrame

        log.debug(">>> outputRange()")
        log.debug("  start =" + str(start))
        log.debug("  end =" + str(end))

        return (start, end)

    def preSequence(self):
        """preSequence()
        This function serves as hook for custom scripts to add functionality before a task starts exporting anything with the sequence"""
        pass

    def postSequence(self):
        """preSequence()
        This function serves as hook for custom scripts to add functionality on completion of exporting the contents of the sequence"""
        pass

    def startTask(self):
        """startTask()
        Called when task reaches head of the export queue and begins execution"""
        TaskCallbacks.call(TaskCallbacks.onTaskStart, self)

        self.preSequence()

        # Build resolved path
        self._makePath()

    def _makePath(self):
        """_makePath()
        Resolve export path and make directories as neccessary."""
        # check export root exists, if not create
        dirPath = util.asUnicode(os.path.dirname(self.resolvedExportPath()))

        try:
            # If the destination path doesnt already exist, create it.
            util.filesystem.makeDirs(dirPath)

        # Set error in case of exceptions
        except Exception, e:
            self.setError("Failed to create directory '%s'\n%s" %
                          (dirPath, str(e)))

        if not self.error():
            # Ensure write access to this path
            if not util.filesystem.access(dirPath, os.W_OK | os.X_OK):
                self.setError(
                    "Insufficient permissions to write to directory '%s'" % util.asUtf8(dirPath))

    def taskStep(self):
        """taskStep()
        Called every frame until task completes.
        Return True value to indicate task requires more steps.
        Return False value to indicate synchronous processing of the task is complete.
        The task may continue to run in the background.
        """
        return False

    def progress(self):
        """progress()
        Returns a float value 0..1 to indicate progress of task.
        The task is considered complete once the progress is reported as 1.
        """
        if self._finished:
            return 1.0
        else:
            return 0.0

    def finishTask(self):
        """finishTask()
        Called once Task has signaled completion.  Sub-classes should call this base implementation. """
        TaskCallbacks.call(TaskCallbacks.onTaskFinish, self)

        self._finished = True
        self.postSequence()

        # Release cloned items
        self._item = None
        self._trackitem = None
        self._track = None
        self._sequence = None
        self._clip = None
        self._source = None
        self._fileinfo = None

    def _sequenceHasAudio(self, sequence):
        for track in sequence.audioTracks():
            for trackItem in track:
                if trackItem.source():
                    return True
        return False

    def hasValidItem(self):
        """Get if the task is able to run on the item it was initialised with."""
        supportedTypes = self._preset.supportedItems()
        supported = False
        if TaskPresetBase.kSequence & supportedTypes:
            supported |= isinstance(self._item, (Sequence,))
        if TaskPresetBase.kTrackItem & supportedTypes:
            supported |= isinstance(
                self._item, (TrackItem,)) and self._item.mediaType() == TrackItem.kVideo
        if TaskPresetBase.kAudioTrackItem & supportedTypes:
            supported |= isinstance(
                self._item, (TrackItem,)) and self._item.mediaType() == TrackItem.kAudio
        if TaskPresetBase.kClip & supportedTypes:
            supported |= isinstance(self._item, (Clip,))

        return supported

    def supportedType(self, item):
        """Interface for defining what type of items a Task Supports.
        Return True to indicate @param item is of supported type"""
        # Derived classes must override to specify what types they support.
        # Typically this is Sequence or TrackItem.
        if type(self) is TaskBase:
            return True
        return False

    def isExportingItem(self, item):
        """ Check if this task is already including an item in its export.
            Used for preventing duplicates when collating shots into a single script. """
        return False

    def deleteTemporaryFile(self, filePath):
        """ Delete a file which is an artifact of the export, but should be removed after it's finished.
            Returns whether the file was successfully deleted."""

        # The reason for this behaviour is that we have occasional problems with tests failing on Windows
        # when removing temporary log files after a transcode.  We don't want the export to be considered
        # in error when this happens, but it should be logged.
        try:
            os.unlink(filePath)
            return True
        except Exception, e:
            log.info("Deleting temporary file failed: %s" % str(e))
            return False


class TaskGroup(ITask):
    """ TaskGroup is a Task which maintains a list of child Tasks. """

    def __init__(self):
        ITask.__init__(self)
        self._children = []

    def addChild(self, child):
        """ Add a child to the list. """
        self._children.append(child)

    def children(self):
        """ Get the TaskGroup's children. """
        return self._children

    def getLeafTasks(self):
        """ Get a list of all leaf tasks recursively, i.e. those with no child tasks. """
        leafTasks = []
        for child in self._children:
            if issubclass(type(child), TaskGroup):
                leafTasks.extend(child.getLeafTasks())
            else:
                leafTasks.append(child)  # Leaf
        return leafTasks

    def addToQueue(self):
        try:
            ITask.addToQueue(self)
        except NotImplementedError:
            pass

    def progress(self):
        """ Get the group progress.  Returns a value based on the progress of child tasks. """
        progress = 0.0
        count = len(self._children)
        for child in self._children:
            progress += (child.progress() / count)
        return progress


class TaskPresetBase(ITaskPreset):
    """TaskPreset is the base class from which all Task Presets must derrive
    The purpose of a Task Preset is to store and data which must be serialized to file
    and shared between the Task and TaskUI user interface component"""

    def __init__(self, parentType, presetName):
        """Initialise Exporter Preset Base Class
        @param parentType : Task type to which this preset object corresponds
        @param presetName : Name of preset"""
        ITaskPreset.__init__(self)
        self._name = presetName
        self._properties = {}
        self._nonPersistentProperties = {}
        self._parentType = parentType
        self._savePath = ""
        self._delete = False
        self._readOnly = False
        self._project = None
        self._skipOffline = True

        # Lists of MediaSources with comps to either render or skip
        self._compsToRender = []
        self._compsToSkip = []

    def initialiseCallbacks(self, exportStructure):
        """ When parent ExportStructure is opened in the ui, initialise is called
        for each preset. Register any callbacks here.
        """
        pass

    def __eq__(self, other):
        """Implement equal operator. This will compare the TaskPreset name
           and it's properties. This method will ignore difference between
           lists an tuples, since the same TaskPreset can be copied and
           the only change existing is a list instead of a tuple."""

        if not isinstance(other, TaskPresetBase):
            return False

        if self.name() != other.name():
            return False

        selfPropsKeys = sorted(self.properties().keys())
        otherPropsKeys = sorted(other.properties().keys())
        if selfPropsKeys != otherPropsKeys:
            return False

        exportTemplateKey = 'exportTemplate'
        if exportTemplateKey in selfPropsKeys:
            selfPropsKeys.remove(exportTemplateKey)
            selfExportTemplate = self.properties()[exportTemplateKey]
            otherExportTemplate = other.properties()[exportTemplateKey]

            # the exportTemplate is a nested list and when loaded into the GUI a list
            # an be changed to a tuple so that change needs to be ignored
            if not self.__exportTemplate__eq__(selfExportTemplate, otherExportTemplate):
                return False

        for key in selfPropsKeys:
            selfProp = self.properties()[key]
            otherProp = other.properties()[key]

            # ignore differences between tuples and list
            if type(selfProp) in (types.ListType, types.TupleType):
                selfProp = list(selfProp)
                otherProp = list(otherProp)

            if selfProp != otherProp:
                return False
        return True

    def __ne__(self, other):
        """Implements not equal operator using self.__eq__ """
        return not self.__eq__(other)

    def __repr__(self):
        return "%s - %s" % (str(self._name), str(self._properties))

    def __exportTemplate__eq__(self, selfExportTemplate, otherExportTemplate):
        """__eq__ method for the export template property. The export template is
        a list (or tuple) of pairs with format [ path , export template ], and
        these pairs can be a list or a tuple as well. This method compares two
        exportTemplates ignoring the difference between list and tuples, so
        (path1,export1) , (path2,export2)) == [[path1,export1] , [path2,export2]]
        And the order of the pairs is ignored as well. A unique key is defined to
        order the list with the 'path', 'export template type' and 'file type'. So
        ((path1,export1),(path2,export2)) == ((path2,export2),(path1,export1))"""

        selfExportTemplate = list(selfExportTemplate)
        otherExporteTemplate = list(otherExportTemplate)
        if len(selfExportTemplate) != len(otherExportTemplate):
            return False

        # sort export template by path, export type and file_type
        def getSortKey(item):
            """Method to define the key to sort the expor templates. The key is a
            combination of the path, export type and the file type.
            @return string with path, export type and file type concatenated """
            path = item[0]
            exportTemplate = item[1]
            exportTemplateType = type(exportTemplate)

            # exportTemplate can be None, in this case the file type is set to an
            # empty string
            fileType = ''
            if isinstance(exportTemplate, TaskPresetBase):
                fileType = exportTemplate.properties().get('file_type', '')

            return '%s%s%s' % (path, exportTemplateType, fileType)

        # order both exportTemplates with a specific key.
        selfExportTemplate = sorted(selfExportTemplate, key=getSortKey)
        otherExportTemplate = sorted(otherExportTemplate, key=getSortKey)

        # transform every pair (path,exportTemplate) into lists,
        # removing the difference between list and tuples again
        selfExportTemplate = [list(item) for item in selfExportTemplate]
        otherExportTemplate = [list(item) for item in otherExportTemplate]

        # finally compare paths and export templates
        selfExportTemplatePaths = [item[0] for item in selfExportTemplate]
        otherExportTemplatePaths = [item[0] for item in otherExportTemplate]
        if selfExportTemplatePaths != otherExportTemplatePaths:
            return False

        selfExportTemplateItems = [item[1] for item in selfExportTemplate]
        otherExportTemplateItems = [item[1] for item in otherExportTemplate]
        if selfExportTemplateItems != otherExportTemplateItems:
            return False

        return True

    def name(self):
        """Return Preset Name"""
        return self._name

    def setName(self, name):
        """Set Preset Name"""
        self._name = name

    def summary(self):
        """Called by Hiero to get a summary of the preset settings as a string."""
        return ""

    def properties(self):
        """properties()
        Return the dictionary which is used to persist data within this preset.
        @return dict
        """
        return self._properties

    def nonPersistentProperties(self):
        """nonPersistentProperties()
        Return the dictionary which contains properties not persisted within the preset.
        Properties which are only relevant during a single session.
        @return dict
        """
        return self._nonPersistentProperties

    def ident(self):
        """ident(self)
        Returns a string used for identifying the type of task"""
        return classBasename(self._parentType)

    def parentType(self):
        """parentType(self)
        Returns a the parent Task type for this TaskPreset.
        @return TaskPreet class type"""
        return self._parentType

    def addDefaultResolveEntries(self, resolver):
        """addDefaultResolveEntries(self, resolver)
        Create resolve entries for default resolve tokens shared by all task types.
        @param resolver : ResolveTable object"""

        resolver.addResolver("{version}", "Version string 'v#', defined by the number (#) set in the Version section of the export dialog",
                             lambda keyword, task: task.versionString())
        resolver.addResolver("{project}", "Name of the parent project of the item being processed",
                             lambda keyword, task: task.projectName())
        resolver.addResolver("{projectroot}", "Project root path specified in the Project Settings",
                             lambda keyword, task: task.projectRoot())
        resolver.addResolver("{hierotemp}", "Temp directory as specified in the Application preferences",
                             lambda keyword, task: ApplicationSettings().value("cacheFolder"))

        resolver.addResolver("{timestamp}", "Export start time in 24-hour clock time (HHMM)",
                             lambda keyword, task: task.timeStamp().strftime("%H%M"))
        resolver.addResolver("{hour24}", "Export start time hour (24-hour clock)",
                             lambda keyword, task: task.timeStamp().strftime("%H"))
        resolver.addResolver("{hour12}", "Export start time hour (12-hour clock)",
                             lambda keyword, task: task.timeStamp().strftime("%I"))
        resolver.addResolver("{ampm}", "Locale's equivalent of either AM or PM.",
                             lambda keyword, task: task.timeStamp().strftime("%p"))
        resolver.addResolver(
            "{minute}", "Export start time minute [00,59]", lambda keyword, task: task.timeStamp().strftime("%M"))
        resolver.addResolver(
            "{second}", "Export start time second [00,61] - '61' accounts for leap/double-leap seconds", lambda keyword, task: task.timeStamp().strftime("%S"))
        resolver.addResolver(
            "{day}", "Locale's abbreviated weekday name, [Mon-Sun]", lambda keyword, task: task.timeStamp().strftime("%a"))
        resolver.addResolver("{fullday}", "Locale's full weekday name",
                             lambda keyword, task: task.timeStamp().strftime("%A"))
        resolver.addResolver(
            "{month}", "Locale's abbreviated month name, [Jan-Dec]", lambda keyword, task: task.timeStamp().strftime("%b"))
        resolver.addResolver("{fullmonth}", "Locale's full month name",
                             lambda keyword, task: task.timeStamp().strftime("%B"))
        resolver.addResolver(
            "{DD}", "Day of the month as a decimal number, [01,31]", lambda keyword, task: task.timeStamp().strftime("%d"))
        resolver.addResolver(
            "{MM}", "Month as a decimal number, [01,12]", lambda keyword, task: task.timeStamp().strftime("%m"))
        resolver.addResolver(
            "{YY}", "Year without century as a decimal number [00,99]", lambda keyword, task: task.timeStamp().strftime("%y"))
        resolver.addResolver("{YYYY}", "Year with century as a decimal number",
                             lambda keyword, task: task.timeStamp().strftime("%Y"))

        resolver.addResolver("{user}", "Current username",
                             lambda keyword, task: getpass.getuser())

    def addCustomResolveEntries(self, resolver):
        """addCustomResolveEntries(self, resolver)
        Impliment this function on custom export tasks to add resolve entries specific to that class.

        @param resolver : ResolveTable object"""
        pass

    def addUserResolveEntries(self, resolver):
        """addUserResolveEntries(self, resolver)
        Override this function to add user specific resolve tokens.
        When adding task specific tokens in derrived classes use TaskBase.addCustomResolveEntries().
        This is reserved for users to extend the available tokens.

        @param resolver : ResolveTable object"""
        pass

    def createResolver(self):
        """createResolver(self)
        Instantiate ResolveTable, add default and custom resolve entries
        return ResolveTable object"""
        resolver = ResolveTable()
        self.addDefaultResolveEntries(resolver)
        self.addCustomResolveEntries(resolver)
        self.addUserResolveEntries(resolver)
        return resolver

    def getResolveEntryCount(self):
        """getResolveEntryCount(self) (DEPRICATED)
        Return the number of resolve entries in the resolve table"""
        return self.resolveEntryCount()

    def resolveEntryCount(self):
        """resolveEntryCount(self)
        Return the number of resolve entries in the resolve table"""

        resolver = self.createResolver()
        return resolver.entryCount()

    def resolveEntryName(self, index):
        """resolveEntryName(self, index)
        return ResolveEntry name/token by index"""
        resolver = self.createResolver()
        return resolver.entryName(index)

    def resolveEntryDescription(self, index):
        """resolveEntryDescription(self, index)
        return ResolveEntry description by index"""
        resolver = self.createResolver()
        return resolver.entryDescription(index)

    def setSavePath(self, path):
        """setSavePath(self, path)
        Set the save path of the preset in order to ensure it is saved to the path it was loaded from"""
        self._savePath = path

    def savePath(self):
        """savePath(self)
        Return the path from which this preset was loaded. Will return None if this preset was not loaded from file"""
        return self._savePath

    def setProject(self, project):
        """Set the Project() object which this preset is associated"""
        self._project = project

    def project(self):
        """Return the Project with which this preset is associated. If this is a local preset returns None"""
        if self._project and not self._project.isNull():
            return self._project
        return None

    def setReadOnly(self, readOnly):
        """Set Read Only flag on preset, not enforced internally"""
        self._readOnly = readOnly

    def readOnly(self):
        """Return the read only flag for this preset"""
        return self._readOnly

    def markedForDeletion(self):
        """Return True if this preset is marked for deletion. Delete will be performed at save"""
        return self._delete

    def setMarkedForDeletion(self, markedForDeletion=True):
        """Set this preset as marked for deletion. Delete will be performed at save"""
        self._delete = markedForDeletion

    def skipOffline(self):
        """skipOffline()
        Returns True if flag has been set to skip any offline TrackItems
        @return bool"""
        return self._skipOffline

    def setSkipOffline(self, skip):
        """skipOffline(bool)
        Set flag to skip offline TrackItems during export.
        @param bool"""
        self._skipOffline = skip

    def setCompsToRender(self, comps):
        """ Set the list of comps to render. """
        self._compsToRender = comps
        self._compsToSkip = []

    def setCompsToSkip(self, comps):
        """ Set the list of comps to skip. """
        self._compsToRender = []
        self._compsToSkip = comps


# Added for legacy support
class TaskPreset(TaskPresetBase):
    """Deprecated - Use TaskPresetBase"""

    def __init__(self, parentType, presetName):
        TaskPresetBase.__init__(self, parentType, presetName)
        pass


def GetFramerates():
    return defaultFrameRates()

# The codec list needs to be in sync with Apps/Nuke/Plugins/FileIO/src/codecWhitelist.cpp
# TODO Use a common source to generate both lists.
# see the bottom of this file for some nuke python script to run in the script editor in Nuke to get these lists:
# AN: Replace this static list with a dynamically generated one, using the Write Node settings.


def getMov64CodecList():
    """Returns a list of supported mov64 codecs."""
    codeclist = [
        'apcn\tApple ProRes 422',
        'apch\tApple ProRes 422 HQ',
        'apcs\tApple ProRes 422 LT',
        'apco\tApple ProRes 422 Proxy',
        Default('ap4h\tApple ProRes 4444'),
        'ap4x\tApple ProRes 4444 XQ',
        'AVdn\tAvid DNxHD Codec',
        'rle \tAnimation',
        'mp1v\tMPEG-1 Video',
        'mp4v\tMPEG-4 Video',
        'jpeg\tPhoto - JPEG',
        'png \tPNG',
        'v210\tUncompressed 10-bit 4:2:2']
    return codeclist


def getMov64DNxHDProperties():
    return {
        ("codec_profile", "dnxhd_codec_profile"): (Default("DNxHD 444 10-bit 440Mbit"),
                                                   "DNxHD 422 10-bit 220Mbit",
                                                   "DNxHD 422 8-bit 220Mbit",
                                                   "DNxHD 422 8-bit 145Mbit",
                                                   "DNxHD 422 8-bit 36Mbit"),
        ("data_range", "dnxhd_encode_video_range"): ("Full Range", Default("Video Range"))}


def getMov64Properties():
    return {
        "bitrate": IntRange(0, 400000, 20000),
        "bitrate_tolerance": IntRange(0, 40000000, 40000000),
        "gop_size": IntRange(0, 30, 12),
        "b_frames": IntRange(0, 30, 0),
        "quality_min": IntRange(0, 50, 2),
        "quality_max": IntRange(0, 50, 31)}


def getMov32Properties():
    return {
        "settings": QuicktimeSettings(),
        ("YCbCr Matrix", "ycbcr_matrix_type"): ("Auto", "Rec 601", "Rec 709", "Nuke Legacy", "Nuke Legacy MPEG")}


def getMovProperties():
    return OrderedDict([
        ("codec", QuicktimeCodec()),
        ("encoder", (Default("mov64"), "mov32"))])


class RenderTaskPreset(TaskPresetBase):
    """RenderTaskPreset is a specialization of the TaskPreset which contains parameters
    associated with generating Nuke render output. """

    def __init__(self, taskType, name, properties):
        """Initialise presets to default values"""
        TaskPresetBase.__init__(self, taskType, name)
        defaultFileType = "dpx"
        self._properties["file_type"] = defaultFileType
        self._properties["reformat"] = {"to_type": "None",
                                        "scale": 1.0,
                                        "resize": "width",
                                        "center": True,
                                        "filter": "Cubic"}
        self._properties["colourspace"] = "default"
        self._properties["channels"] = "rgb"

        # Update preset with loaded data
        self._properties.update(properties)

        self._codecSettings = {}

        # Because this key has changed, its possible that existing presest will exist without this key.
        # When the _properties dict is updated with the preset information, reformat will be overwritten
        if not "to_type" in self._properties["reformat"]:
            self._properties["reformat"]["to_type"] = "None"

        movFps = GetFramerates()

        # mov64 encoding on all platforms
        movEncoderProperties = {"mov64": {"properties": getMov64Properties(),
                                          "dnxhdproperties": getMov64DNxHDProperties()}}

        # Add mov32 on windows and osx
        if ((sys.platform.startswith("win32")) or (sys.platform.startswith("darwin"))):
            movEncoderProperties["mov32"] = {"properties": getMov32Properties(),
                                             "dnxhdproperties": dict()}

        self._setCodecSettings("mov", "mov", "mov", True, getMovProperties(
        ), encoderProperties=movEncoderProperties)

        self._setCodecSettings("dpx", "dpx", "DPX", False, {"datatype": ("8 bit", Default("10 bit"), "12 bit", "16 bit"),
                                                            ("Fill", "fill"): False, ("Big Endian", "bigEndian"): True,
                                                            "transfer": ("(auto detect)", "user-defined", "printing density", "linear", "log", "unspecified video", "SMPTE 240M", "CCIR 709-1", "CCIR 601-2 system B/G", "CCIR 601-2 system M", "NTSC", "PAL", "Z linear", "Z homogeneous")})
        self._setCodecSettings("dpx", "dpx", "DPX", False,
                               OrderedDict([("datatype", ("8 bit", Default("10 bit"), "12 bit", "16 bit")),
                                            (("Fill", "fill"), False),
                                            (("Big Endian", "bigEndian"), True),
                                            ("transfer", ("(auto detect)", "user-defined", "printing density", "linear", "log", "unspecified video", "SMPTE 240M", "CCIR 709-1", "CCIR 601-2 system B/G", "CCIR 601-2 system M", "NTSC", "PAL", "Z linear", "Z homogeneous"))]))
        self._setCodecSettings("dpx", "dpx", "DPX", False, {"datatype": ("8 bit", Default("10 bit"), "12 bit", "16 bit"),
                                                            ("Fill", "fill"): False, ("Big Endian", "bigEndian"): True,
                                                            "transfer": ("(auto detect)", "user-defined", "printing density", "linear", "log", "unspecified video", "SMPTE 240M", "CCIR 709-1", "CCIR 601-2 system B/G", "CCIR 601-2 system M", "NTSC", "PAL", "Z linear", "Z homogeneous")})

        self._setCodecSettings("exr", "exr", "EXR", False, OrderedDict([
            ("datatype", ("16 bit half", "32 bit float")),
            ("compression", ("none", Default("Zip (1 scanline)"), "Zip (16 scanline)",
                             "PIZ Wavelet (32 scanlines)", "RLE", "B44", "B44A", "DWAA", "DWAB")),
            (("compression level", "dw_compression_level"),
             FloatRange(0.0, 500.0, 45.0)),
            ("metadata", ("default metadata", "no metadata", "default metadata and exr/*",
                          "all metadata except input/*", "all metadata")),
            (("do not attach prefix", "noprefix"), False),
            ("interleave", ("channels, layers and views",
                            "channels and layers", "channels")),
            (("standard layer name format", "standard_layer_name_format"), False),
            (("write full layer names",
              "write_full_layer_names"), False),
            (("truncate channel names",
              "truncateChannelNames"), False),
            (("write ACES compliant EXR", "write_ACES_compliant_EXR"), False)]))
        self._setCodecSettings("pic", "pic", "PIC", False, OrderedDict())
        self._setCodecSettings("cin", "cin", "Cineon", False, OrderedDict())
        self._setCodecSettings("jpeg", "jpg", "JPEG", False, {(
            "quality", '_jpeg_quality'): FloatRange(0.0, 1.0, 0.75)})
        self._setCodecSettings("png", "png", "PNG", False, {
                               "datatype": ("8 bit", "16 bit")})
        self._setCodecSettings("sgi", "sgi", "SGI", False, OrderedDict(
            [("datatype", ("8 bit", "16 bit")), ("compression", ("none", Default("RLE")))]))
        self._setCodecSettings("tiff", "tif", "TIFF", False, OrderedDict(
            [("datatype", ("8 bit", "16 bit", "32 bit float")), ("compression", ("none", "PackBits", "LZW", Default("Deflate")))]))
        self._setCodecSettings("targa", "tga", "Targa", False, {
                               "compression": ("none", Default("RLE"))})

        if self._properties["file_type"] not in self._codecSettings.keys():
            if self._properties["file_type"] == "ffmpeg":
                self._properties["file_type"] = "mov"
            elif self._properties["file_type"] == "mov":
                self._properties["file_type"] = "ffmpeg"
            else:
                # arbitrarily pick the first key
                self._properties["file_type"] = defaultFileType

    def _setCodecSettings(self, codecType, extension, fullname, isVideo, properties, encoderProperties=None):
        """Build dictionary of format settings.\n
        @param encoderProperties - (optional) dict of properties to extend codec properties by, based on encoder selection"""
        self._codecSettings[codecType] = {"extension": extension, "fullname": fullname,
                                          "properties": properties, "isVideo": isVideo, "encoderProperties": encoderProperties}

    def _getCodecSettingsDefault(self, codecType, codecKey):
        """Search codec settings for a matching codecKey and return a default value. \n
        @param codecType - format identifier (mov, dpx, jpeg etc..)\n
        @param codecKey - codec settings key"""

        dictionary = self._codecSettings[codecType]["properties"]
        for key, value in dictionary.iteritems():
            if hasattr(key, "__iter__"):
                key = key[1]

            if key == codecKey:
                if isinstance(value, FloatRange):
                    return value.default()
                elif hasattr(value, "__iter__"):
                    for item in value:
                        if isinstance(item, Default):
                            return item
                elif isinstance(value, (types.IntType, types.FloatType, types.LongType, basestring)):
                    return value
                else:
                    return str(value)
        return None

    def addCustomResolveEntries(self, resolver):
        """addCustomResolveEntries(self, resolver)
        RenderTaskPreset adds specialized tokens specific to this type of export, such as {ext} which returns the output format extnesion.
        @param resolver : ResolveTable object"""
        #resolver.addResolver("{height}", "Height component of output format", lambda keyword, task: self.height())
        #resolver.addResolver("{width}", "Width component of output format", lambda keyword, task: self.width())
        #resolver.addResolver("{pixelaspect}", "Pixel Aspect of output format", lambda keyword, task: self.pixelAspect())
        resolver.addResolver(
            "{ext}", "Extension of the file to be output", lambda keyword, task: self.extension())

    # def height (self):
    #  if "height" in self._properties["reformat"]:
    #    return self._properties["reformat"]["height"]
    #  elif isinstance(self._item, hiero.core.Sequence):
    #    return self._sequence.format().height()
    #  else:
    #    self._source.height()

    # def width (self):
    #  if "width" in self._properties["reformat"]:
    #    return self._properties["reformat"]["width"]
    #  elif isinstance(self._item, hiero.core.Sequence):
    #    return self._sequence.format().width()
    #  else:
    #    self._source.width()

    # def pixelAspect (self):
    #  if "pixelAspect" in self._properties["reformat"]:
    #    return self._properties["reformat"]["pixelAspect"]
    #  elif isinstance(self._item, hiero.core.Sequence):
    #    return self._sequence.format().pixelAspect()
    #  else:
    #    self._source.pixelAspect()

    def summary(self):
        properties = []

        fileType = self._properties["file_type"]

        if fileType in self._properties:
            properties = self._properties[fileType]
            codecproperties = []

            # This is to prevent the hideous quicktime settings hex string appearing in the summary
            for key, value in properties.iteritems():
                if not (fileType == "mov" and key == "settings"):
                    codecproperties.append(value)

            return str("(%s - %s)" % (fileType, ", ".join(str(value) for value in codecproperties)))
        else:
            return str("(%s)" % fileType)

    def extension(self):
        return self.codecSettings()['extension']

    def codecName(self):
        return self.codecSettings()['fullname']

    def codecProperties(self):
        return self.codecSettings()['properties']

    def codecSettings(self):
        return self._codecSettings[self._properties['file_type']]


class RenderTaskPresetBase(RenderTaskPreset):
    """RenderTaskPresetBase (Deprecated)
     - Use RenderTaskPreset"""
    pass


class FolderTask(TaskBase):
    """ Task which just creates an empty folder. """

    def __init__(self, initDict):
        TaskBase.__init__(self, initDict)


class FolderTaskPreset(TaskPresetBase):
    """ Preset which can be used for creating an empty folder. """

    def __init__(self, name, properties):
        TaskPresetBase.__init__(self, FolderTask, name)
        self.properties().update(properties)


def tagsFromSelection(selection, includeChildren=False, includeParents=False):
    """Returns a list of tuples for tag/parent type pairs"""

    def _items(selection):
        # Generator function for extracting the actual item from ItemWrappers
        for item in selection:
            if isinstance(item, ItemWrapper):
                if not item.ignore():
                    yield item.item()
            else:
                yield item

    tags = []
    for item in _items(selection):
        if isinstance(item, TrackItem):
            # Collect all tags from trackItem
            tags.extend([(tag, TrackItem) for tag in item.tags()])
            if includeParents:
                tags.extend(tagsFromSelection(
                    [item.parent()], includeChildren=False, includeParents=True))

        elif isinstance(item, (VideoTrack, AudioTrack)):
            tags.extend([(tag, type(item)) for tag in item.tags()])
            if includeChildren:
                for trackItem in item:
                    tags.extend(tagsFromSelection(
                        [trackItem, ], includeChildren))
            elif includeParents:
                tags.extend(tagsFromSelection(
                    [item.parent()], includeChildren=False, includeParents=True))

        elif isinstance(item, Sequence):
            # Traverse sequence and collect any tags
            sequence = item
            tags.extend([(tag, Sequence) for tag in sequence.tags()])
            if includeChildren:
                for track in sequence.videoTracks() + sequence.audioTracks():
                    tags.extend(tagsFromSelection([track, ], includeChildren))

        elif isinstance(item, Clip):
            tags.extend([(tag, Clip) for tag in item.tags()])

    return tags


def mediaSourceExportReadPath(source, useFirstFrame):
    """ Get the path to include in exports from a media source.  If the source is an nk script
        return the comp write path.  If useFirstFrame is True, for file sequences will return e.g.
        clip.0001.dpx rather than clip.%04d.dpx """
    path = source.firstpath() if useFirstFrame else source.fileinfos()[
        0].filename()
    try:
        compInfo = CompSourceInfo(source)
        if compInfo.isComp():
            path = compInfo.writePath
            if useFirstFrame:
                path = path % compInfo.firstFrame
    except:
        pass
    return path


def mediaSourceExportFileHead(source):
    """ Get the filename head from a media source, fixing for use as a keyword. """
    head = source.filenameHead()

    # If the filename is e.g. bob.%03.dpx, filenameHead() will return everything up the frame number, including the
    # '. just before it, so 'bob.'.  This is not very helpful when resolving the keywords, so check for the string
    # ending with a '.' and if so remove it.
    if head.endswith('.'):
        head = head[:-1]

    return head


# some script to run in Nuke to get the ffmpeg formats, codecs and macro block decision lists
#n = nuke.createNode("Write")
#
# def printEnum(k):
#  print "["
# values = k.values()
# for i in values:
#    print "\"" + i + "\", "
#  print "]"
#
# n.knobs()["file_type"].setValue("ffmpeg")
#
# printEnum(n.knobs()["format"])
# printEnum(n.knobs()["codec"])
# printEnum(n.knobs()["mbDecision"])
