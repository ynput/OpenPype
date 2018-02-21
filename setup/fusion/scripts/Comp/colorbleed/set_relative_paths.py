import os
import re


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
        

def makeRelativePath(root, path):
    try:
        return "Comp:\{0}".format(os.path.relpath(os.path.abspath(fusion.MapPath(path)), root))
    except ValueError:
        print("Warning -- Can't define relative path for: {0}".format(path))
        return path
    
def pathToCurrentComp():
    return comp.GetAttrs()["COMPS_FileName"]

        
def cbRelativePaths():
    userResponse = comp.AskUser("Make paths relative",
                    {
                        1:{1:"Loaders", 2:"Checkbox", "Name":"Loaders", "NumAcross":3, "Default":1},
                        2:{1:"Savers", 2:"Checkbox", "Name":"Savers", "NumAcross":3, "Default":1},
                        3:{1:"Proxy", 2:"Checkbox", "Name":"Proxy", "NumAcross":3, "Default":1},
                        4:{1:"SelectedOnly", 2:"Checkbox", "Name":"Selected Only", "Default":0}
                    }
                    )
        
    if userResponse:
        
        root = pathToCurrentComp()
        if not root:
            raise RuntimeError("Fusion file has not been saved. Can't make paths relative")
        if root:
            root = os.path.dirname(root)
            
        # set root
        os.chdir(root)
            
        doLoaders = userResponse['Loaders']
        doSavers = userResponse['Savers']
        doProxy = userResponse['Proxy']
        doSelectedOnly = bool(userResponse['SelectedOnly'])
        
        

        with FusionLockComp('Make paths relative'):
            toolsDict = comp.GetToolList(doSelectedOnly)
            for i, tool in toolsDict.items():
                toolId = tool.ID
                if toolId == "Loader" or toolId == "Saver":
                    tool_a = tool.GetAttrs()
                    if (doLoaders or doProxy) and toolId == "Loader":
                        clipTable = tool_a['TOOLST_Clip_Name']
                        altclipTable = tool_a['TOOLST_AltClip_Name']
                        startTime = tool_a['TOOLNT_Clip_Start']
                        
                        # Preserve global in
                        oldGlobalIn = tool.GlobalIn[comp.CurrentTime]
                        
                        if doLoaders:
                            for n, name in clipTable.items():
                                if name:
                                    newPath = makeRelativePath(root, name)
                                    tool.Clip[startTime[n]] = newPath
                                    
                        if doProxy:
                            for n, name in altclipTable.items():
                                if name:
                                    newPath = makeRelativePath(root, name)
                                    tool.ProxyFilename[startTime[n]] = newPath

                        # Set global in (to what we preserved)
                        tool.GlobalIn[comp.CurrentTime] = oldGlobalIn
                                        
                    if doSavers and toolId == "Saver":
                        for i, name in tool_a['TOOLST_Clip_Name'].items():
                            if name:
                                newPath = makeRelativePath(root, name)
                                tool.Clip[comp.TIME_UNDEFINED] = newPath

cbRelativePaths()
                                
            