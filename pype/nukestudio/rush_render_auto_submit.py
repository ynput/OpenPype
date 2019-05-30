# Example to submit a Transcode render to a Rush render farm, automatically start the render, and open IRush

# This assumes some default settings about render cpus (+any) and batch frames (20)
# If you would like to just send the relevant Sequence information to the default submit script (name, path to Nuke script, framerange) look at the rushRenderStartIrush.py example

import hiero.core
import hiero.core.nuke as nuke
from hiero.exporters.FnSubmission import Submission
import re
import os
import sys
import subprocess
import time

# Create a Task to handle Sequences and Clips for Transcoding. This is pulled from site-packages/hiero/exporters/FnLocalNukeRender.py
# Modify this to pass the information you want to your own external processes


class RushRenderTask(hiero.core.TaskBase):
    def __init__(self, initDict, scriptPath):
        hiero.core.TaskBase.__init__(self, initDict)
        self._scriptPath = scriptPath
        self._pySubmit = os.path.splitext(self._scriptPath)[0] + ".py"
        self._logFileName = os.path.splitext(self._scriptPath)[0] + ".log"
        self._jobDoneFile = os.path.splitext(self._scriptPath)[0] + ".done"
        self._logFile = None
        self._submitJob = None
        self._finished = False
        self._progress = 0.0
        self._frame = 0
        self._first = 0
        if isinstance(self._item, Sequence):
            self._last = self._sequence.duration() - 1
        if isinstance(self._item, Clip):
            start, end = self.outputRange(
                ignoreRetimes=True, clampToSource=False)
            self._last = end
        if isinstance(self._item, TrackItem):
            start, end = self.outputRange(
                ignoreRetimes=True, clampToSource=False)
            self._last = end
        self._jobTitle = os.path.splitext(
            os.path.basename(self._scriptPath))[0]

    # Send the rush script to Rush and get back the rush job ID
    def sendToRush(self, scriptPath, first, last, jobTitle):
        self.createRushSubmitScript(jobTitle, first, last, scriptPath)
        cmd = "eval " + "python " + os.path.abspath(self._pySubmit)
        self._submitJob = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._jobID = self._submitJob.stdout.readline().split(' ')[
            2].split('\n')[0]

    # Process is considered a Background task when taskStep() returns False and progress is less than 1.0
    def taskStep(self):
        if self._finished == True:
            return True
        else:
            return False

    def startTask(self):
        self._logFile = open(self._logFileName, 'w')
        self.sendToRush(self._scriptPath, self._first,
                        self._last, self._jobTitle)

        # Create a Rush jobdonecommand to send render "Done" status back to Hiero.
        doneCmd = "rush %s -jobdonecommand 'touch %s'" % (
            self._jobID, self._jobDoneFile)
        subprocess.Popen(doneCmd, shell=True)

    # Abort will not affect the external render. If you want to abort the rush render from Hiero then grab the jobID and run a rush -end jobID from here
    def forcedAbort(self):
        # If process is running, terminate
        returncode = None
        if returncode is None:
            self._submitJob.terminate()
            self.parseErrorOutput()
        return

    """
  Get the render progress.
  """

    def progress(self):
        # If the job done file has been created by rush -jobdonecommand then the task is finished
        if os.access(self._jobDoneFile, os.R_OK):
            self._finished = True
            # Delete the rush job done command files
            os.unlink(self._jobDoneFile)

        if self._finished:
            return 1.0
        return float(self._progress)

    """
  Parse progress from the log file.
  """

    def parseProgressOutput(self):
        rushStatus = "rush -lfi " + self._jobID + \
            " 2>&1 |awk '/Done/ {print $4}'"
        rushProgress = subprocess.Popen(
            rushStatus, shell=True, stdout=subprocess.PIPE)
        try:
            doneProgress = rushProgress.stdout.readline().split("%")[1]
        except:
            doneProgress = 0
        if doneProgress:
            self._progress = float(int(doneProgress) / 100)

    """
  Parse any errors in the log file.
  """

    def parseErrorOutput(self):
        file = open(self._logFileName, 'r')
        output = file.readlines()
        file.close()
        errorString = ""
        for line in output:
            if line:
                matches = re.search(
                    "[\[\w\]\.\:]*(warning:|error:|failure:|cannot\sbe\sexecuted).*", line, re.IGNORECASE)
                if matches:
                    errorString += line
        if errorString != "":
            self.setError(errorString)

    """
  Clean up after render.
  """

    def finishTask(self):
        # Close log file
        self._logFile.close()
        # parse log file for error output
        self.parseErrorOutput()

        # If options not set, delete nk and log files
        if not self._preset._properties["keepNukeScript"]:
            # clean up the script
            os.unlink(self._scriptPath)
            os.unlink(self._logFileName)

    # Create the Rush submit script that gets sent to Rush.
    def createRushSubmitScript(self, jobTitle, start, end, scriptPath):
        renderCommand = " -xi " + scriptPath
        batch = 20
        submitInfo = """#!/usr/bin/env python
import os
import sys
import subprocess
import re

if sys.platform in 'linux2':
    nukePath = '/usr/local/Nuke6.3v7/Nuke6.3'
if sys.platform in 'darwin':
    nukePath = '/Applications/Nuke6.3v7/Nuke6.3v7.app/Nuke6.3v7'

# Parse jobid from rush submit
def ParseJobid(rushoutfile):
    rushout = open(rushoutfile, 'r')
    rushout_lines = ""
    while 1:
        line = rushout.readline()
        if ( line == "" ):
            break
        rushout_lines += line
    print rushout_lines
    rushout.close()
    return(re.search("RUSH_JOBID.(\S+)", rushout_lines).groups()[0])

# SUBMIT THE JOB IF NO ARGS SPECIFIED
if len(sys.argv) <= 1:
    if ( os.environ.has_key("RUSH_ISDAEMON") ):   # Prevent 'network worm' style recursion
        sys.exit(1)

    # User should change these as needed
    sfrm   = {3}                                  # Start frame
    efrm   = {4}                                 # End frame
    batch  = {5}                                  # Batch frames (1 disables)
    scene  = "{2}"                                # Scene file to render
    logdir = scene + ".log"                     # Log directory based on scene pathname

    # Create log directory if none
    if ( not os.path.isdir(logdir) ):
        os.mkdir(logdir, 0777)

    # SUBMIT THE JOB
    #    Save output to a temp file so we can parse back jobid..
    #
    tmpfile = "/var/tmp"
    if ( os.path.isdir("c:/temp") ):
        tmpfile = "c:/temp"
    tmpfile = "%s/submit-out.%d" % ( tmpfile, os.getpid() )

    # Submit the job
    submit = os.popen("rush -submit > " + tmpfile, 'w')
    submit.write("title    {0}\\n" +
                 "ram      250\\n" +
                 "frames   %d-%d,%d\\n" % ( sfrm, efrm, batch) +
                 "logdir   %s\\n" % logdir +
                 "command  python %s -render %s %s %s\\n" % ( sys.argv[0], scene, batch, efrm ) +
                 "cpus     +any=5@1\\n")
    err = submit.close()

    # Read submit output, parse jobid, remove tmp file
    os.environ["RUSH_JOBID"] = ParseJobid(tmpfile);
    os.remove(tmpfile)

    # Submit Failed
    if ( err or os.environ["RUSH_JOBID"] == "" ):
        sys.exit(1)

    # Submit OK
    print "--- Starting irush.."
    os.system("irush -button Frames")
    sys.exit(0)

# RENDERING ON REMOTE MACHINE?
if ( sys.argv[1] == "-render" ):
    scene   = sys.argv[2]
    batch   = int(sys.argv[3])
    lastfrm = int(sys.argv[4])
    sfrm    = int(os.environ["RUSH_FRAME"])
    efrm    = int(os.environ["RUSH_FRAME"]) + batch - 1
    if ( efrm > lastfrm ):
        efrm = lastfrm

    # PRINT FRAMES BEING RENDERED
    if ( sfrm == efrm ):
        print "--- Working on frame %d" % sfrm
    else:
        print "--- Working on frames %d - %d" % ( sfrm, efrm )

    # START RENDER, CHECK FOR ERRORS
    cmd = nukePath + " -xi -F %d-%d %s" % ( sfrm, efrm, sys.argv[2] )
    print "--- Executing: %s" % cmd
    sys.stdout.flush()
    err = os.system(cmd)
    if err:
        print "--- Render failed (EXIT CODE=%s)" % (err >> 8)  # Failed? show error code
        sys.exit(1)                                            # 'sys.exit(1)' tells rush frame "Fail"

    print "--- Render OK"                                      # Worked?
    sys.exit(0)                                                # 'sys.exit(0)' tells rush frame "Done"

# BAD ARGUMENT
stderr.write("%s: unknown argument %s\\n" % ( sys.argv[0], sys.argv[1] ) )
sys.exit(1)

"""
        submitInfo = submitInfo.format(
            jobTitle, renderCommand, scriptPath, start, end, batch)
        f = open(self._pySubmit, 'w')
        f.write(submitInfo)
        f.close()

# Create a Submission and add your Task


class RushRenderSubmission(Submission):
    def __init__(self):
        Submission.__init__(self)

    def addJob(self, jobType, initDict, filePath):
        return RushRenderTask(initDict, filePath)


# Add the Custom Task Submission to the Export Queue
registry = hiero.core.taskRegistry
registry.addSubmission("Send to Rush", RushRenderSubmission)
