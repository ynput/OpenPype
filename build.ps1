Write-Host "Building Pype ..."
Write-Host "Detecting host Python ..."
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "!!! Python not detected"
}
$version_command = @'
import sys
print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))
'@

$p = & python -c $version_command
$env:PYTHON_VERSION = $p
$m = $p -match '(\d+)\.(\d+)'
if(-not $m) {
  Write-Host "!!! Cannot determine version".
  return 1
}
# We are supporting python 3.6 and up
if(($matches[1] -lt 3) -or ($matches[2] -lt 7)) {
  Write-Host "FAILED Version [ $p ] is old and unsupported"
  return 1
}
Write-Host "... got [ $p ]"
Write-Host "Creating virtual env ..."
& python -m venv venv
Write-Host "Entering venv..."
try {
  . (".\venv\Scripts\Activate.ps1")
}
catch {
  Write-Host "!!! Failed to activate."
  Write-Host $_.Exception.Message
  return 1
}
& pip install -r .\requirements.txt
& python setup.py build
deactivate
