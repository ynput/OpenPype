
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
        
        
def pairs(n):
    it = iter(n)
    return zip(it, it)
    

def duplicateWithInputConnections():

    with FusionLockComp("Duplicate With Input Connections"):
        originalTools = comp.GetToolList(True)
        if not originalTools:
            return # nothing selected
            
        comp.Copy()
        comp.SetActiveTool()
        comp.Paste()
        
        duplicateTools = comp.GetToolList(True)
        
        for i, tool in originalTools.iteritems():
            dupToolInputs = duplicateTools[i].GetInputList()
            
            for j, input in tool.GetInputList().iteritems():
                if input.GetAttrs()['INPB_Connected']:
                    if j in dupToolInputs:
                        if dupToolInputs[j].GetAttrs()['INPB_Connected']:
                            print (" Both connected. ")
                        else:
                            dupToolInputs[j].ConnectTo(input.GetConnectedOutput())
                            if dupToolInputs[j].GetAttrs()['INPB_Connected']:
                                print (" Connection Successful ")
            
        

duplicateWithInputConnections()
                                
            