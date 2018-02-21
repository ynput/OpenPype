
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
        

        
def f1():
    with FusionLockComp('Selected Backgrounds to 32bit'):
        toolsDict = comp.GetToolList(True)
        if toolsDict:
            for i, tool in toolsDict.items():
                if tool.ID == "Background":
                    tool.Depth = 5

f1()
                                
            