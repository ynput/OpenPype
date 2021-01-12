$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName

& "$($pype_root)\venv\Scripts\Activate.ps1"

python "$($pype_root)\start.py" settings --dev
deactivate