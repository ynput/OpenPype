
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

idList = set(["BrightnessContrast", "ColorCorrector"])
attrName = "PreDividePostMultiply"

with FusionLockComp("BC & CC set PreMultiplyPostDivide to 1"):
    toolsDict = comp.GetToolList(False)
    if toolsDict:
        for i, tool in toolsDict.items():
            if tool.ID in idList:
                for input in tool.GetInputList().values():
                    setattr(tool, attrName, 1.0)