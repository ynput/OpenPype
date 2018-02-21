
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
    with FusionLockComp('Loaders to 32bit'):
        toolsDict = comp.GetToolList(False)
        if toolsDict:
            for i, tool in toolsDict.items():
                if tool.ID == "Loader":
                    tool.Depth = 5

f1()
                                
            