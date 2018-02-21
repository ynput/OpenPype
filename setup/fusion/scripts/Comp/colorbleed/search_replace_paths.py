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
        

def replaceStr(inputString, srchFor, srchTo, caseSensitive=True):
    if caseSensitive:
        return inputString.replace(srchFor, srchTo)
    else:
        regex = re.compile(re.escape(srchFor), re.IGNORECASE)
        return regex.sub(srchTo, inputString)

        
def searchReplaceLoaderSavers():
    userResponse = comp.AskUser("Repath All Loaders",
                    {1:{1:"Loaders", 2:"Checkbox", "Name":"Loaders", "NumAcross":3, "Default":1},
                     2:{1:"Savers", 2:"Checkbox", "Name":"Savers", "NumAcross":3, "Default":1},
                     3:{1:"Proxy", 2:"Checkbox", "Name":"Proxy", "NumAcross":3, "Default":1},
                     4:{1:"Source", 2:"Text", "Name":"Enter pattern to search for"},
                     5:{1:"Replacement", 2:"Text", "Name":"Enter the replacement path"},
                     6:{1:"Valid", 2:"Checkbox", "Name":"Check If New Path is Valid", "Default":1},
                     7:{1:"CaseSensitive", 2:"Checkbox", "Name":"Case Sensitive", "Default":1},
                     8:{1:"SelectedOnly", 2:"Checkbox", "Name":"Selected Only", "Default":0},
                     9:{1:"PreserveGlobalIn", 2:"Checkbox", "Name":"Preserve Global In Point", "Default":1}
                     }
                )
        
    if userResponse:
        srchFor = userResponse['Source']
        if not srchFor:
            raise RuntimeError("No source string specified.")
            
        srchTo = userResponse['Replacement']
        if not srchTo:
            raise RuntimeError("No replacement string specified.")
            
        doLoaders = userResponse['Loaders']
        doSavers = userResponse['Savers']
        doProxy = userResponse['Proxy']
        doValidate = userResponse['Valid']
        doCaseSensitive = userResponse['CaseSensitive']
        doSelectedOnly = bool(userResponse['SelectedOnly'])
        doPreserveGlobalIn = bool(userResponse['PreserveGlobalIn'])
                

        with FusionLockComp('Path Remap - "{0}" to "{1}"'.format(srchFor, srchTo)):
            toolsDict = comp.GetToolList(doSelectedOnly)
            for i, tool in toolsDict.items():
                toolId = tool.ID
                if toolId == "Loader" or toolId == "Saver":
                    tool_a = tool.GetAttrs()
                    if (doLoaders or doProxy) and toolId == "Loader":
                        clipTable = tool_a['TOOLST_Clip_Name']
                        altclipTable = tool_a['TOOLST_AltClip_Name']
                        startTime = tool_a['TOOLNT_Clip_Start']
                        
                        if doPreserveGlobalIn:
                            oldGlobalIn = tool.GlobalIn[comp.CurrentTime]
                        
                        if doLoaders:
                            for n, name in clipTable.items():
                            #for i in table.getn(clipTable):
                                if name:
                                    newPath = replaceStr(name, srchFor, srchTo, doCaseSensitive)
                                    print (name, newPath)
                                    if not doValidate or os.path.exists(comp.MapPath(newPath)):
                                        tool.Clip[startTime[n]] = newPath
                                    else:
                                        print( "FAILED : New clip does not exist; skipping sequence.\n  {0} .. {1}".format(name, newPath))
                                    
                        if doProxy:
                            for n, name in altclipTable.items():
                                if name:
                                    newPath = replaceStr(name, srchFor, srchTo, doCaseSensitive)
                                    if not doValidate or os.path.exists(comp.MapPath(newPath)):
                                        tool.ProxyFilename[startTime[n]] = newPath
                                    else:
                                        print( "FAILED : New proxy clip does not exist; skipping sequence.\n  {0} .. {1}".format(name, newPath))

                        if doPreserveGlobalIn:
                            tool.GlobalIn[comp.CurrentTime] = oldGlobalIn
                                        
                    if doSavers and toolId == "Saver":
                        for i, name in tool_a['TOOLST_Clip_Name'].items():
                            newPath = replaceStr(name, srchFor, srchTo, doCaseSensitive)
                            if not doValidate or os.path.exists(os.path.dirname(comp.MapPath(newPath))):
                                tool.Clip[comp. ] = newPath
                            else:
                                print( "FAILED : Output directory does not exist; skipping saver.\n  {0} .. {1}".format(name, newPath))

searchReplaceLoaderSavers()
                                
            