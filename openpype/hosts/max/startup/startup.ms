-- OpenPype Init Script
(
    local sysPath = dotNetClass "System.IO.Path"
	local sysDir = dotNetClass "System.IO.Directory"
	local localScript = getThisScriptFilename()
    local startup = sysPath.Combine (sysPath.GetDirectoryName localScript) "startup.py"

    local pythonpath = systemTools.getEnvVariable "MAX_PYTHONPATH"
    systemTools.setEnvVariable "PYTHONPATH" pythonpath
    
    /*opens the create menu on startup to ensure users are presented with a useful default view.*/
    max create mode

    python.ExecuteFile startup
)
