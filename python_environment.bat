@echo OFF
echo Entering Python environment...

set CB_PYTHON_VERSION=2.7

where /Q python.exe
if ERRORLEVEL 1 (
    if EXIST C:\Python27\python.exe (
        echo Adding C:\Python27 to PATH
        set "PATH=%PATH%;C:\Python27"
		goto:has-python
    ) else (
        echo Adding embedded python (pipeline)
        set "PATH=%PATH%;%CB_APP_SHARED%\python\standalone\%CB_PYTHON_VERSION%\bin"
		goto:has-python
    )
)
:has-python

:: Python universal (non-compiled)
set PYTHONPATH=%PYTHONPATH%;%CB_APP_SHARED%\python\universal\site-packages

:: Python version/windows-specific
:: set PYTHONPATH=%PYTHONPATH%;%CB_APP_SHARED%\python\win\%CB_PYTHON_VERSION%

:: Python standalone (compiled to version)
if NOT "%CB_PYTHON_STANDALONE%" == "0" (
    echo Entering Python Standalone environment...
    set PYTHONPATH=%PYTHONPATH%;%CB_APP_SHARED%\python\standalone\%CB_PYTHON_VERSION%\site-packages
)
