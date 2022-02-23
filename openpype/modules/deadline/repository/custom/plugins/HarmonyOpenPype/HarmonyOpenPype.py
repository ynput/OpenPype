from System import *
from System.Diagnostics import *
from System.IO import *
from System.Text import *

from Deadline.Plugins import *
from Deadline.Scripting import *

def GetDeadlinePlugin():
    return HarmonyOpenPypePlugin()
    
def CleanupDeadlinePlugin( deadlinePlugin ):
    deadlinePlugin.Cleanup()
    
class HarmonyOpenPypePlugin( DeadlinePlugin ):

    def __init__( self ):
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
        self.CheckExitCodeCallback += self.CheckExitCode

    def Cleanup( self ):
        print("Cleanup")
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback
        
        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
        
    def CheckExitCode( self, exitCode ):
        print("check code")
        if exitCode != 0:
            if exitCode == 100:
                self.LogInfo( "Renderer reported an error with error code 100. This will be ignored, since the option to ignore it is specified in the Job Properties." )
            else:
                self.FailRender( "Renderer returned non-zero error code %d. Check the renderer's output." % exitCode )
    
    def InitializeProcess( self ):
        self.PluginType = PluginType.Simple
        self.StdoutHandling = True
        self.PopupHandling = True
        
        self.AddStdoutHandlerCallback( "Rendered frame ([0-9]+)" ).HandleCallback += self.HandleStdoutProgress
    
    def HandleStdoutProgress( self ):
        startFrame = self.GetStartFrame()
        endFrame = self.GetEndFrame()
        if( endFrame - startFrame + 1 != 0 ):
            self.SetProgress( 100 * ( int(self.GetRegexMatch(1)) - startFrame + 1 ) / ( endFrame - startFrame + 1 ) )
    
    def RenderExecutable( self ):
        version = int( self.GetPluginInfoEntry( "Version" ) )
        exe = ""
        exeList = self.GetConfigEntry( "Harmony_RenderExecutable_" + str(version) )
        exe = FileUtils.SearchFileList( exeList )
        if( exe == "" ):
            self.FailRender( "Harmony render executable was not found in the configured separated list \"" + exeList + "\". The path to the render executable can be configured from the Plugin Configuration in the Deadline Monitor." )
        return exe
        
    def RenderArgument( self ):
        renderArguments = "-batch"

        if self.GetBooleanPluginInfoEntryWithDefault( "UsingResPreset", False ):
            resName = self.GetPluginInfoEntryWithDefault( "ResolutionName", "HDTV_1080p24" )
            if resName == "Custom":
                renderArguments += " -res " + self.GetPluginInfoEntryWithDefault( "PresetName", "HDTV_1080p24" )
            else:
                renderArguments += " -res " + resName
        else:
            resolutionX = self.GetIntegerPluginInfoEntryWithDefault( "ResolutionX", -1 )
            resolutionY = self.GetIntegerPluginInfoEntryWithDefault( "ResolutionY", -1 )
            fov = self.GetFloatPluginInfoEntryWithDefault( "FieldOfView", -1 )
        
            if resolutionX > 0 and resolutionY > 0 and fov > 0:
                renderArguments += " -res " + str( resolutionX ) + " " + str( resolutionY ) + " " + str( fov )
        
        camera = self.GetPluginInfoEntryWithDefault( "Camera", "" )
        
        if not camera == "":
            renderArguments += " -camera " + camera
        
        startFrame = str( self.GetStartFrame() )
        endFrame = str( self.GetEndFrame() )
                
        renderArguments += " -frames " + startFrame + " " + endFrame
        
        if not self.GetBooleanPluginInfoEntryWithDefault( "IsDatabase", False ):
            sceneFilename = self.GetPluginInfoEntryWithDefault( "SceneFile", self.GetDataFilename() )
            sceneFilename = RepositoryUtils.CheckPathMapping( sceneFilename )
            renderArguments += " \"" + sceneFilename + "\""
        else:
            environment = self.GetPluginInfoEntryWithDefault( "Environment", "" )
            renderArguments += " -env " + environment
            job = self.GetPluginInfoEntryWithDefault( "Job", "" )
            renderArguments += " -job " + job
            scene = self.GetPluginInfoEntryWithDefault( "SceneName", "" )
            renderArguments += " -scene " + scene
            version = self.GetPluginInfoEntryWithDefault( "SceneVersion", "" )
            renderArguments += " -version " + version
        
        #tempSceneDirectory = self.CreateTempDirectory( "thread" + str(self.GetThreadNumber()) )
        #preRenderScript = 
        rendernodeNum = 0
        scriptBuilder = StringBuilder()
        
        while True:
            nodeName = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "Node", "" )
            if nodeName == "":
                break
            nodeType = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "Type", "Image" )
            if nodeType == "Image":
                nodePath = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "Path", "" )
                nodeLeadingZero = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "LeadingZero", "" )
                nodeFormat = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "Format", "" )
                nodeStartFrame = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "StartFrame", "" )
                
                if not nodePath == "":
                    scriptBuilder.AppendLine("node.setTextAttr( \"" + nodeName + "\", \"drawingName\", 1, \"" + nodePath + "\" );")
                    
                if not nodeLeadingZero == "":
                    scriptBuilder.AppendLine("node.setTextAttr( \"" + nodeName + "\", \"leadingZeros\", 1, \"" + nodeLeadingZero + "\" );")
                
                if not nodeFormat == "":
                    scriptBuilder.AppendLine("node.setTextAttr( \"" + nodeName + "\", \"drawingType\", 1, \"" + nodeFormat + "\" );")
                    
                if not nodeStartFrame == "":
                    scriptBuilder.AppendLine("node.setTextAttr( \"" + nodeName + "\", \"start\", 1, \"" + nodeStartFrame + "\" );")
            
            if nodeType == "Movie":
                nodePath = self.GetPluginInfoEntryWithDefault( "Output" + str( rendernodeNum ) + "Path", "" )
                if not nodePath == "":
                    scriptBuilder.AppendLine("node.setTextAttr( \"" + nodeName + "\", \"moviePath\", 1, \"" + nodePath + "\" );")
            
            rendernodeNum += 1
        
        tempDirectory = self.CreateTempDirectory( "thread" + str(self.GetThreadNumber()) )
        preRenderScriptName = Path.Combine( tempDirectory, "preRenderScript.txt" )
        
        File.WriteAllText( preRenderScriptName, scriptBuilder.ToString() )
        
        preRenderInlineScript = self.GetPluginInfoEntryWithDefault( "PreRenderInlineScript", "" )
        if preRenderInlineScript:
            renderArguments += " -preRenderInlineScript \"" + preRenderInlineScript +"\""
        
        renderArguments += " -preRenderScript \"" + preRenderScriptName +"\""
        
        return renderArguments
