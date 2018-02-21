

class FusionLockComp(object):
    def __init__(self, undoQueueName="Script CMD"):
        # Lock flow
        comp.Lock()
        # Start undo event
        comp.StartUndo(undoQueueName)

    def __enter__(self):
        return None

    def __exit__(self, type, value, traceback):
        comp.EndUndo(True)
        comp.Unlock()


with FusionLockComp("Reload clip time ranges"):
    toolsDict = comp.GetToolList(True)
    if toolsDict:
        for i, tool in toolsDict.items():
            if tool.ID != "Loader":
                continue

            tool_a = tool.GetAttrs()
            clipTable = tool_a['TOOLST_Clip_Name']
            altclipTable = tool_a['TOOLST_AltClip_Name']
            startTime = tool_a['TOOLNT_Clip_Start']
            oldGlobalIn = tool.GlobalIn[comp.CurrentTime]

            for n, c in clipTable.items():
                tool.Clip[startTime[n]] = tool.Clip[startTime[n]]

            for n, c in altclipTable.items():
                tool.ProxyFilename[startTime[n]] = tool.ProxyFilename[startTime[n]]

            tool.GlobalIn[comp.CurrentTime] = oldGlobalIn
