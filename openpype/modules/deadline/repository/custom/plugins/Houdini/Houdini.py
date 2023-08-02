#!/usr/bin/env python3

from __future__ import absolute_import
from System import *
from System.Diagnostics import *
from System.IO import *

from Deadline.Plugins import DeadlinePlugin, PluginType
from Deadline.Scripting import RepositoryUtils, SystemUtils, FileUtils, SlaveUtils, ClientUtils

import io
import os
import re
import socket
import traceback
import six
from six.moves import range

def GetDeadlinePlugin():
    return HoudiniPlugin()

def CleanupDeadlinePlugin( deadlinePlugin ):
    deadlinePlugin.Cleanup()

class HoudiniPlugin (DeadlinePlugin):
    completedFrames = 0
    ropType = ""

    def __init__( self ):
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
        self.PreRenderTasksCallback += self.PreRenderTasks
        self.PostRenderTasksCallback += self.PostRenderTasks

        self.TempThreadDirectory = None
        self.SimTrackerArgs = ""

    def Cleanup(self):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
        del self.PreRenderTasksCallback
        del self.PostRenderTasksCallback

    def InitializeProcess( self ):
        self.SingleFramesOnly = False
        self.StdoutHandling = True
        self.PopupHandling = True

        self.AddStdoutHandlerCallback( "(Couldn't find renderer.*)" ).HandleCallback += self.HandleStdoutRenderer
        self.AddStdoutHandlerCallback( "(Error: Unknown option:.*)" ).HandleCallback += self.HandleStdoutUnknown
        self.AddStdoutHandlerCallback( "(Error: .*)" ).HandleCallback += self.HandleStdoutError
        self.AddStdoutHandlerCallback(r"(ERROR\s*\|.*)").HandleCallback += self.HandleStdoutError #Arnold errors
        self.AddStdoutHandlerCallback(r"\[Error\].*").HandleCallback += self.HandleStdoutError
        self.AddStdoutHandlerCallback( ".*(Redshift cannot operate with less than 128MB of free VRAM).*" ).HandleCallback += self.HandleStdoutError
        self.AddStdoutHandlerCallback( ".*(No licenses could be found to run this application).*" ).HandleCallback += self.HandleStdoutLicense
        self.AddStdoutHandlerCallback( ".*ALF_PROGRESS ([0-9]+)%.*" ).HandleCallback += self.HandleStdoutFrameProgress
        self.AddStdoutHandlerCallback( ".*Render Time:.*" ).HandleCallback += self.HandleStdoutFrameComplete
        self.AddStdoutHandlerCallback( ".*Finished Rendering.*" ).HandleCallback += self.HandleStdoutDoneRender
        self.AddStdoutHandlerCallback( ".*ROP type: (.*)" ).HandleCallback += self.SetRopType
        self.AddStdoutHandlerCallback( ".*?(\d+)% done.*" ).HandleCallback += self.HandleStdoutFrameProgress
        self.AddStdoutHandlerCallback( "\[render progress\] ---[ ]+(\d+) percent" ).HandleCallback += self.HandleStdoutFrameProgress
        self.AddStdoutHandlerCallback( "(License error: No license found)").HandleCallback += self.HandleStdoutLicense
        self.AddStdoutHandlerCallback( "RMAN_PROGRESS *([0-9]+)%" ).HandleCallback += self.HandleStdoutFrameProgress

        # redshift errors if output path does not exist
        self.AddStdoutHandlerCallback( "Output file locked or path not available for writing. Skipping frame." ).HandleCallback += self.HandleStdoutOutputPathUnavailable

        self.AddPopupHandler( ".*Streaming SIMD Extensions Not Enabled.*", "OK" )

    def RenderExecutable( self ):
        version = self.GetPluginInfoEntryWithDefault( "Version", "18.5" ).replace( ".", "_" )
        return self.GetRenderExecutable( "Houdini" + version + "_Hython_Executable", "Houdini " + version)

    def RenderArgument(self):
        ifdFilename = self.GetPluginInfoEntryWithDefault( "IFD", "" )
        ifdFilename = RepositoryUtils.CheckPathMapping( ifdFilename )

        outputFilename = self.GetPluginInfoEntryWithDefault( "Output", "" )
        outputFilename = RepositoryUtils.CheckPathMapping( outputFilename )

        scene = self.GetPluginInfoEntryWithDefault( "SceneFile", self.GetDataFilename() )
        scene = RepositoryUtils.CheckPathMapping( scene )

        regionRendering = self.GetBooleanPluginInfoEntryWithDefault( "RegionRendering", False )
        singleRegionJob = self.IsTileJob()
        singleRegionFrame = str(self.GetStartFrame())
        singleRegionIndex = self.GetCurrentTaskId()

        simJob = self.GetBooleanPluginInfoEntryWithDefault( "SimJob", False )

        wedgeNum = -1
        try:
            wedgeNum = self.GetIntegerPluginInfoEntryWithDefault("WedgeNum", "-1")
        except:
            pass

        scene = scene.replace("\\","/")
        outputFilename = outputFilename.replace("\\", "/")
        ifdFilename = ifdFilename.replace("\\", "/")

        if SystemUtils.IsRunningOnWindows():
            if scene.startswith( "/" ) and scene[0:2] != "//":
                scene = "/" + scene
            if outputFilename.startswith( "/" ) and outputFilename[0:2] != "//":
                outputFilename = "/" + outputFilename
            if ifdFilename.startswith( "/" ) and ifdFilename[0:2] != "//":
                ifdFilename = "/" + ifdFilename
        else:
            if scene.startswith( "/" ) and scene[0:2] == "//":
                scene = scene[1:len(scene)]
            if outputFilename.startswith( "/" ) and outputFilename[0:2] == "//":
                outputFilename = outputFilename[1:len(outputFilename)]
            if ifdFilename.startswith( "/" ) and ifdFilename[0:2] == "//":
                ifdFilename = ifdFilename[1:len(ifdFilename)]

        # Construct the command line options, to be used by hrender_dl.py and return them.
        hrender = Path.Combine( self.GetPluginDirectory(),"hrender_dl.py" )
        arguments = [ "\"%s\"" % hrender ]

        if simJob:
            machineNameOrIpAddress = ""
            trackerPort = self.GetIntegerConfigEntry( "Houdini_SimTracker_Tracker_Port" )
            if self.GetBooleanPluginInfoEntryWithDefault( "SimRequiresTracking", True ):
                self.LogInfo( "Sim Job: Checking which machine is running the tracking process" )

                # Need to figure out which Worker is rendering the first task for this job.
                currentJob = self.GetJob()
                tasks = RepositoryUtils.GetJobTasks( currentJob, True )

                if tasks.GetTask(0).TaskStatus != "Rendering":
                    self.FailRender( "Sim Job: Cannot determine which machine is running the tracking process because the first task for this job is not in the rendering state" )

                trackerMachineSlave = tasks.GetTask(0).TaskSlaveName
                if trackerMachineSlave == "":
                    self.FailRender( "Sim Job: Cannot determine which machine is running the tracking process because the first task for this job is not being rendered by another Worker" )

                slaveInfo = RepositoryUtils.GetSlaveInfo( trackerMachineSlave, True )
                self.LogInfo( "Sim Job: Worker \"" + slaveInfo.SlaveName + "\" is running the tracking proccess" )


                if not self.GetConfigEntry( "Houdini_SimTracker_Use_IP_Address" ):
                    machineNameOrIpAddress = SlaveUtils.GetMachineNames([slaveInfo])[0]
                    self.LogInfo( "Sim Job: Connecting to Worker machine using host name \"" + machineNameOrIpAddress + "\"" )
                else:
                    machineNameOrIpAddress = SlaveUtils.GetMachineIPAddresses([slaveInfo])[0]
                    self.LogInfo( "Sim Job: Connecting to Worker machine using IP address \"" + machineNameOrIpAddress + "\"" )

            arguments.append( "-s %s \"%s\" %s" % (singleRegionFrame, machineNameOrIpAddress, trackerPort) )
        elif regionRendering and singleRegionJob:
            arguments.append( "-f %s %s 1" % (singleRegionFrame, singleRegionFrame) )
        else:
            arguments.append( "-f %s %s 1" % (self.GetStartFrame(), self.GetEndFrame()) )

        width = self.GetIntegerPluginInfoEntryWithDefault( "Width", 0 )
        height = self.GetIntegerPluginInfoEntryWithDefault( "Height", 0 )
        if( width > 0 and height > 0 ):
            arguments.append( "-r %s %s" % (width, height) )

        if( len(outputFilename) > 0 ):
            arguments.append( "-o \"%s\"" % outputFilename )
        if( len(ifdFilename) > 0 ):
            arguments.append( "-i \"%s\"" % ifdFilename )

        if self.GetBooleanPluginInfoEntryWithDefault( "IgnoreInputs", False ):
            arguments.append( "-g" )

        arguments.append( "-d %s" % self.GetPluginInfoEntry( "OutputDriver" ) )
        if regionRendering:
            xStart = 0
            xEnd = 0
            yStart = 0
            yEnd = 0
            currTile = 0
            if singleRegionJob:
                currTile = singleRegionIndex
                xStart = self.GetFloatPluginInfoEntryWithDefault("RegionLeft"+str(singleRegionIndex),0)
                xEnd = self.GetFloatPluginInfoEntryWithDefault("RegionRight"+str(singleRegionIndex),0)
                yStart = self.GetFloatPluginInfoEntryWithDefault("RegionBottom"+str(singleRegionIndex),0)
                yEnd = self.GetFloatPluginInfoEntryWithDefault("RegionTop"+str(singleRegionIndex),0)
            else:
                currTile = self.GetIntegerPluginInfoEntryWithDefault( "CurrentTile", 1 )
                xStart = self.GetFloatPluginInfoEntryWithDefault( "RegionLeft", 0 )
                xEnd = self.GetFloatPluginInfoEntryWithDefault( "RegionRight", 0 )
                yStart = self.GetFloatPluginInfoEntryWithDefault( "RegionBottom", 0 )
                yEnd = self.GetFloatPluginInfoEntryWithDefault( "RegionTop", 0 )

            arguments.append( "-t %s %s %s %s %s" % ( currTile, xStart, xEnd, yStart, yEnd ) )

        if wedgeNum > -1:
            arguments.append( "-wedgenum %s" % wedgeNum )

        gpuList = self.GetGpuOverrides()
        if len( gpuList ) > 0:

            gpus = ",".join( gpuList )
            arguments.append( "-gpu %s" % gpus )

            if self.GetBooleanPluginInfoEntryWithDefault( "OpenCLUseGPU", 1 ):
                self.SetEnvironmentVariable( "HOUDINI_OCL_DEVICETYPE", "GPU" )
                self.SetEnvironmentVariable( "HOUDINI_OCL_VENDOR", "" )
                self.SetEnvironmentVariable( "HOUDINI_OCL_DEVICENUMBER", gpuList[ self.GetThreadNumber() % len( gpuList ) ] )

        self.TempThreadDirectory = self.CreateTempDirectory(str( self.GetThreadNumber()))
        arguments.append( "-tempdir \"%s\"" % self.TempThreadDirectory )

        abortOnLicenseFail = 1 if self.GetBooleanConfigEntryWithDefault( "AbortOnArnoldLicenseFail", True ) else 0
        arguments.append( "-arnoldAbortOnLicenseFail %s" % abortOnLicenseFail )

        arguments.append( "\"%s\"" % scene )

        return " ".join( arguments )

    def GetGpuOverrides( self ):
        resultGPUs = []

        # If the number of gpus per task is set, then need to calculate the gpus to use.
        gpusPerTask = self.GetIntegerPluginInfoEntryWithDefault( "GPUsPerTask", 0 )
        gpusSelectDevices = self.GetPluginInfoEntryWithDefault( "GPUsSelectDevices", "" )

        if self.OverrideGpuAffinity():
            overrideGPUs = self.GpuAffinity()
            if gpusPerTask == 0 and gpusSelectDevices != "":
                gpus = gpusSelectDevices.split( "," )
                notFoundGPUs = []
                for gpu in gpus:
                    if int( gpu ) in overrideGPUs:
                        resultGPUs.append( gpu )
                    else:
                        notFoundGPUs.append( gpu )

                if len( notFoundGPUs ) > 0:
                    self.LogWarning( "The Worker is overriding its GPU affinity and the following GPUs do not match the Workers affinity so they will not be used: " + ",".join( notFoundGPUs ) )
                if len( resultGPUs ) == 0:
                    self.FailRender( "The Worker does not have affinity for any of the GPUs specified in the job." )
            elif gpusPerTask > 0:
                if gpusPerTask > len( overrideGPUs ):
                    self.LogWarning( "The Worker is overriding its GPU affinity and the Worker only has affinity for " + str( len( overrideGPUs ) ) + " gpus of the " + str( gpusPerTask ) + " requested." )
                    resultGPUs =  [ str( gpu ) for gpu in overrideGPUs ]
                else:
                    resultGPUs = [ str( gpu ) for gpu in overrideGPUs if gpu < gpusPerTask ]
            else:
                resultGPUs = [ str( gpu ) for gpu in overrideGPUs ]
        elif gpusPerTask == 0 and gpusSelectDevices != "":
            resultGPUs = gpusSelectDevices.split( "," )

        elif gpusPerTask > 0:
            gpuList = []
            for i in range( ( self.GetThreadNumber() * gpusPerTask ), ( self.GetThreadNumber() * gpusPerTask ) + gpusPerTask ):
                gpuList.append( str( i ) )
            resultGPUs = gpuList

        resultGPUs = list( resultGPUs )

        return resultGPUs

    def PreRenderTasks(self):
        # set 'IS_HOUDINI_RENDERING' to be 'TRUE' so that PreFirstCreate of houdini submission script don't sync file from deadline repository.
        self.SetEnvironmentVariable( 'IS_HOUDINI_RENDERING', "TRUE" )
        # Use Escape License if requested
        slave = self.GetSlaveName().lower()
        ELicSlaves = self.GetConfigEntryWithDefault( "ELicSlaves", "" ).lower().split( ',' )
        if slave in ELicSlaves:
            self.LogInfo( "This Worker will use a Houdini Escape license to render" )
            self.SetEnvironmentVariable("HOUDINI_SCRIPT_LICENSE", "hescape")

        if self.GetBooleanConfigEntryWithDefault( "EnablePathMapping", True ):
            mappings = RepositoryUtils.GetPathMappings( )
            #Remove Mappings with no to path.
            mappings = [ mappingPair for mappingPair in mappings if mappingPair[1] ]
            if len(mappings) >0:
                houdiniPathmap = ""
                if Environment.GetEnvironmentVariable( "HOUDINI_PATHMAP" ) != None:
                    houdiniPathmap = Environment.GetEnvironmentVariable( "HOUDINI_PATHMAP" )

                if houdiniPathmap.endswith( "}" ):
                    houdiniPathmap = houdiniPathmap[:-1]

                for map in mappings:
                    if houdiniPathmap != "":
                        houdiniPathmap += ", "

                    originalPath = map[0].replace("\\","/")
                    newPath = map[1].replace("\\","/")
                    if originalPath != "" and newPath != "":
                        if SystemUtils.IsRunningOnWindows():
                            if newPath.startswith( "/" ) and newPath[0:2] != "//":
                                newPath = "/" + newPath
                        else:
                            if newPath.startswith( "/" ) and newPath[0:2] == "//":
                                newPath = newPath[1:len(newPath)]

                        houdiniPathmap += "\"" + originalPath + "\":\"" + newPath + "\""

                if not houdiniPathmap.startswith("{"):
                    houdiniPathmap = "{"+houdiniPathmap
                if not houdiniPathmap.endswith("}"):
                    houdiniPathmap = houdiniPathmap+"}"

                self.LogInfo("Set HOUDINI_PATHMAP to " + houdiniPathmap )
                self.SetEnvironmentVariable( 'HOUDINI_PATHMAP', houdiniPathmap )

                self.SetRedshiftPathmappingEnv( mappings )

        if self.GetBooleanPluginInfoEntryWithDefault( "SimJob", False ) and self.GetBooleanPluginInfoEntryWithDefault( "SimRequiresTracking", True ) and self.GetCurrentTaskId() == "0":
            self.LogInfo( "Sim Job: Starting Sim Tracker process because this is the first task for this sim job" )

            if six.PY3:
                pythonExe = os.path.join("python3", "python")
            else:
                pythonExe = "dpython"

            if SystemUtils.IsRunningOnWindows():
                pythonExe += ".exe"

            pythonPath = Path.Combine(ClientUtils.GetBinDirectory(), pythonExe)

            version = self.GetPluginInfoEntryWithDefault( "Version", "18.5" ).replace( ".", "_" )

            # Retrieve houdini simtracker executable
            simTracker = self.GetRenderExecutable( "Houdini" + version + "_SimTracker", "Houdini " + version + " SimTracker")

            trackerPort = self.GetIntegerConfigEntry( "Houdini_SimTracker_Tracker_Port" )
            webServicePort = self.GetIntegerConfigEntry( "Houdini_SimTracker_Web_Service_Port" )

            # Check if either of the ports are already in use.
            trackerPortInUse = False
            webServicePortInUse = False

            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', trackerPort))
                s.close()
                s = None
            except:
                s.close()
                s = None
                self.LogWarning( traceback.format_exc() )
                trackerPortInUse = True

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', webServicePort))
                s.close()
                s = None
            except:
                s.close()
                s = None
                self.LogWarning( traceback.format_exc() )
                webServicePortInUse = True

            if trackerPortInUse and webServicePortInUse:
                self.FailRender("Unable to start the Sim Tracker process because tracker port {0} and web service port {1} are in use.".format(trackerPort,webServicePort))
            elif trackerPortInUse:
                self.FailRender("Unable to start the Sim Tracker process because tracker port {0} is in use.".format(trackerPort))
            elif webServicePortInUse:
                self.FailRender("Unable to start the Sim Tracker process because web service port {0} is in use.".format(webServicePort))

            self.SimTrackerArgs = "\"" + simTracker + "\" " + str(trackerPort) + " " + str(webServicePort)
            self.LogInfo("Sim Job: Starting the Sim Tracker process")
            self.StartMonitoredProgram( "SimTracker",  pythonPath, self.SimTrackerArgs, Path.GetDirectoryName( simTracker )  ) # string name, string executable, string arguments, string startupDirectory

        self.LogInfo("Starting Houdini Job")
        self.SetProgress(0)

    def PostRenderTasks(self):
        if self.GetBooleanPluginInfoEntryWithDefault( "SimJob", False ) and self.GetBooleanPluginInfoEntryWithDefault( "SimRequiresTracking", True ) and self.GetCurrentTaskId() == "0":
            self.LogInfo("Sim Job: Waiting for all other tasks for this job to complete before stopping theSim Tracker process")

            incompleteTasks = []

            jobComplete = False
            while not jobComplete:
                if self.IsCanceled():
                    self.FailRender( "Task canceled" )

                SystemUtils.Sleep( 5000 )

                currentJob = self.GetJob()
                tasks = RepositoryUtils.GetJobTasks( currentJob, True )

                jobComplete = True
                for task in tasks:
                    if task.TaskID > 0:
                        if task.TaskStatus != "Completed":
                            taskIdStr = str(task.TaskID)

                            # Don't want to log more than once for any incomplete task.
                            if taskIdStr not in incompleteTasks:
                                incompleteTasks.append( taskIdStr )
                                self.LogInfo("Sim Job, still waiting for task: "+str(task.TaskID))

                            jobComplete = False
                            break

            self.LogInfo("Sim Job: Stopping the Sim Tracker process")
            self.ShutdownMonitoredProgram( "SimTracker" )

        self.LogInfo("Finished Houdini Job")

    def HandleStdoutRenderer(self):
        self.FailRender(self.GetRegexMatch(1))

    def HandleStdoutError(self):
        self.FailRender(self.GetRegexMatch(1))

    def HandleStdoutOutputPathUnavailable(self):
        self.FailRender( "Output file locked or path not available for writing" )

    def HandleStdoutLicense(self):
        self.FailRender(self.GetRegexMatch(1))

    def HandleStdoutUnknown(self):
        self.FailRender( "Bad command line: " + self.RenderArgument() + "\nHoudini Error: " + self.GetRegexMatch(1) )

    def HandleStdoutFrameProgress(self):
        if self.ropType in ("ifd", "rop_ifd"):
            frameCount = self.GetEndFrame() - self.GetStartFrame() + 1
            if frameCount != 0:
                completedFrameProgress = float(self.completedFrames) * 100.0
                currentFrameProgress = float(self.GetRegexMatch(1))
                overallProgress = (completedFrameProgress + currentFrameProgress) / float(frameCount)
                self.SetProgress(overallProgress)
                self.SetStatusMessage( "Progress: " + str(overallProgress) + " %" )

        elif self.ropType in ("arnold", "geometry", "rop_geometry", "wedge", "Octane_ROP", "ris::22"):
            overallProgress = float(self.GetRegexMatch(1))
            self.SetProgress(overallProgress)
            self.SetStatusMessage( "Progress: " + str(overallProgress) + " %" )

    def HandleStdoutFrameComplete(self):
        if self.ropType in ("ifd", "rop_ifd"):
            self.completedFrames = self.completedFrames + 1

    def HandleStdoutDoneRender(self):
        self.SetStatusMessage("Finished Render")
        self.SetProgress(100)

    def SetRopType(self):
        self.ropType = self.GetRegexMatch(1)

    def SetRedshiftPathmappingEnv( self, mappings ):
        try:
            if not mappings:
                return

            self.LogInfo( "Redshift Path Mapping..." )

            # "C:\MyTextures\" "\\MYSERVER01\Textures\" ...
            redshiftMappingRE = re.compile( r"\"([^\"]*)\"\s+\"([^\"]*)\"" )

            oldRSMappingFileName = Environment.GetEnvironmentVariable( "REDSHIFT_PATHOVERRIDE_FILE" )
            if oldRSMappingFileName:
                self.LogInfo( '[REDSHIFT_PATHOVERRIDE_FILE]="%s"' % oldRSMappingFileName )
                with io.open( oldRSMappingFileName, mode="r", encoding="utf-8" ) as oldRSMappingFile:
                    for line in oldRSMappingFile:
                        mappings.extend( redshiftMappingRE.findall( line ) )

            oldRSMappingString = Environment.GetEnvironmentVariable( "REDSHIFT_PATHOVERRIDE_STRING" )
            if oldRSMappingString:
                self.LogInfo( '[REDSHIFT_PATHOVERRIDE_STRING]="%s"' % oldRSMappingString )
                mappings.extend( redshiftMappingRE.findall( oldRSMappingString ) )

            newRSMappingFileName = os.path.join( self.CreateTempDirectory("RSMapping"), "RSMapping.txt" )
            with io.open( newRSMappingFileName, mode="w", encoding="utf-8" ) as newRSMappingFile:
                for mappingPair in mappings:
                    self.LogInfo( u'source: "%s" dest: "%s"' % (mappingPair[0], mappingPair[1] ))
                    newRSMappingFile.write( u'"%s" "%s"\n' % (mappingPair[0], mappingPair[1] ))

            self.LogInfo( '[REDSHIFT_PATHOVERRIDE_FILE] now set to: "%s"' % newRSMappingFileName )
            self.SetEnvironmentVariable( "REDSHIFT_PATHOVERRIDE_FILE", newRSMappingFileName )
        except:
            self.LogWarning( "Failed to set Redshift Pathmapping Environment variable." )
            self.LogWarning( traceback.format_exc())
