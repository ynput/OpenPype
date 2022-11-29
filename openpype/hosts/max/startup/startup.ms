-- OpenPype Init Script
(
    local sysPath = dotNetClass "System.IO.Path"
	local sysDir = dotNetClass "System.IO.Directory"
    local startup = sysPath.Combine (sysPath.GetDirectoryName getSourceFile) "startup.py"

    python.ExecuteFile startup
)