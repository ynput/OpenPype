& .\venv\Scripts\Activate.ps1
sphinx-apidoc.exe -M -e -d 10 -o .\docs\source igniter
sphinx-apidoc.exe -M -e -d 10 -o .\docs\source pype vendor, pype\vendor
python setup.py build_sphinx
deactivate