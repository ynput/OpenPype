$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$repo_root = (Get-Item $script_dir).parent.FullName

$env:PSModulePath = $env:PSModulePath + ";$($repo_root)\tools\modules\powershell"

function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}

function Restore-Cwd() {
    $tmp_current_dir = Get-Location
    if ("$tmp_current_dir" -ne "$current_dir") {
        Write-Color -Text ">>> ", "Restoring current directory" -Color Green, Gray
        Set-Location -Path $current_dir
    }
}

function Get-Container {
    if (-not (Test-Path -PathType Leaf -Path "$($repo_root)\build\docker-image.id")) {
        Write-Color -Text "!!! ", "Docker command failed, cannot find image id." -Color Red, Yellow
        Restore-Cwd
        Exit-WithCode 1
    }
    $id = Get-Content "$($repo_root)\build\docker-image.id"
    Write-Color -Text ">>> ", "Creating container from image id ", "[", $id, "]" -Color Green, Gray, White, Cyan, White
    $cid = docker create $id bash
    if ($LASTEXITCODE -ne 0) {
        Write-Color -Text "!!! ", "Cannot create container." -Color Red, Yellow
        Restore-Cwd
        Exit-WithCode 1
    }
    return $cid
}

function Change-Cwd() {
    Set-Location -Path $repo_root
}

function New-DockerBuild {
    $version_file = Get-Content -Path "$($repo_root)\openpype\version.py"
    $result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
    $openpype_version = $result[0].Groups['version'].Value
    $startTime = [int][double]::Parse((Get-Date -UFormat %s))
    Write-Color -Text ">>> ", "Building OpenPype using Docker ..." -Color Green, Gray, White
    $variant = $args[0]
    $dockerfile = "$($repo_root)\Dockerfile.$variant"
    if (-not (Test-Path -PathType Leaf -Path $dockerfile)) {
        Write-Color -Text "!!! ", "Dockerfile for specifed platform ", "[", $variant, "]", "doesn't exist." -Color Red, Yellow, Cyan, White, Cyan, Yellow
        Restore-Cwd
        Exit-WithCode 1
    }
    Write-Color -Text ">>> ", "Using Dockerfile for ", "[ ", $variant, " ]" -Color Green, Gray, White, Cyan, White
    Write-Color -Text "--- ", "Cleaning build directory ..." -Color Yellow, Gray
    try {
        Remove-Item -Recurse -Force "$($repo_root)\build\*"
    }
    catch {
        Write-Color -Text "!!! ", "Cannot clean build directory, possibly because process is using it." -Color Red, Gray
        Write-Color -Text $_.Exception.Message -Color Red
        Exit-WithCode 1
    }
    Write-Color -Text ">>> ", "Running Docker build ..." -Color Green, Gray, White
    docker build --pull --iidfile $repo_root/build/docker-image.id --build-arg BUILD_DATE=$(Get-Date -UFormat %Y-%m-%dT%H:%M:%SZ) --build-arg VERSION=$openpype_version -t pypeclub/openpype:$openpype_version -f $dockerfile .
    if ($LASTEXITCODE -ne 0) {
        Write-Color -Text "!!! ", "Docker command failed.", $LASTEXITCODE -Color Red, Yellow, Red
        Restore-Cwd
        Exit-WithCode 1
    }
    Write-Color -Text ">>> ", "Copying build from container ..." -Color Green, Gray, White
    $cid = Get-Container

    docker cp "$($cid):/opt/openpype/build/exe.linux-x86_64-3.9" "$($repo_root)/build"
    docker cp "$($cid):/opt/openpype/build/build.log" "$($repo_root)/build"

    $endTime = [int][double]::Parse((Get-Date -UFormat %s))
    try {
        New-BurntToastNotification -AppLogo "$openpype_root/openpype/resources/icons/openpype_icon.png" -Text "OpenPype build complete!", "All done in $( $endTime - $startTime ) secs. You will find OpenPype and build log in build directory."
    } catch {}
    Write-Color -Text "*** ", "All done in ", $($endTime - $startTime), " secs. You will find OpenPype and build log in ", "'.\build'", " directory." -Color Green, Gray, White, Gray, White, Gray
}

Change-Cwd
New-DockerBuild $ARGS
