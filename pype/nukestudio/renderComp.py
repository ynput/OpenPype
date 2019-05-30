from hiero.core import TaskBase, TaskPresetBase, TaskGroup, TaskData
from . FnSubmission import Submission
from hiero.core.FnCompSourceInfo import CompSourceInfo
import copy


class CompRenderTask(TaskBase):
    """ Task for rendering a comp.  This is just a wrapper which creates the actual render task
        through the submission. """

    def __init__(self, initDict, compToRender):
        TaskBase.__init__(self, initDict)

        info = CompSourceInfo(compToRender)

        # Copy the dict so it can be modified
        submissionDict = copy.copy(initDict)

        # Set the start and end frames of the comp
        submissionDict["startFrame"] = info.firstFrame
        submissionDict["endFrame"] = info.lastFrame

        # Add this flag to the dict so the comp will be rendered through the frame
        # server if that was selected.  See FrameServerSubmission.canRenderOnFrameServer
        # for more details.
        submissionDict["renderingComp"] = True
        self.renderTask = self._submission.addJob(
            Submission.kNukeRender, submissionDict, info.nkPath)

    def checkError(self):
        if self.renderTask.error():
            self.setError(self.renderTask.error())

    def startTask(self):
        self.renderTask.startTask()
        self.checkError()

    def taskStep(self):
        self.checkError()
        return self.renderTask.taskStep()

    def progress(self):
        self.checkError()
        return self.renderTask.progress()

    def finishTask(self):
        self.renderTask.finishTask()

    def forcedAbort(self):
        self.renderTask.forcedAbort()


class CompRenderTaskPreset(TaskPresetBase):
    """ Preset for CompRenderTask.  This is only needed
        so the keepNukeScript parameter gets passed through to the
        render tasks generated from the submission. """

    def __init__(self):
        TaskPresetBase.__init__(self, CompRenderTask, "Comp Render")
        self._properties["keepNukeScript"] = True


def createCompRenderTasks(processor, project):
    """ Generate Comp render tasks for the given processor. """

    if processor._preset._compsToRender:
        group = TaskGroup()
        group.setTaskDescription("Comp Renders")
        processor._submission.addChild(group)

        # These tasks aren't generated from a preset in the usual fashion, and most of these
        # parameters don't apply, but we still need to create a TaskData object to initialise with
        taskData = TaskData(CompRenderTaskPreset(),
                            None,
                            "",
                            "",
                            "",
                            processor._exportTemplate,
                            project,
                            resolver=processor._preset.createResolver(),
                            submission=processor._submission)

        for comp in processor._preset._compsToRender:
            task = CompRenderTask(taskData, comp)
            group.addChild(task)
