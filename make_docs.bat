@echo off
echo [92m^>^>^>[0m Generating pype-setup documentation, please wait ...
call "C:\Users\Public\pype_env2\Scripts\activate.bat"

setlocal enableextensions enabledelayedexpansion
set _OLD_PYTHONPATH=%PYTHONPATH%
echo [92m^>^>^>[0m Adding repos path
rem add stuff in repos
call :ResolvePath repodir "..\"

for /d %%d in ( %repodir%*) do (
echo   - adding path %%d
set PYTHONPATH=%%d;!PYTHONPATH!
)

echo [92m^>^>^>[0m Adding python vendors path
rem add python vendor paths
call :ResolvePath vendordir "..\..\vendor\python\"

for /d %%d in ( %vendordir%*) do (
echo   - adding path %%d
set PYTHONPATH=%%d;!PYTHONPATH!
)

echo [92m^>^>^>[0m Setting PYPE_CONFIG
call :ResolvePath pypeconfig "..\pype-config"
set PYPE_CONFIG=%pypeconfig%
echo [92m^>^>^>[0m Setting PYPE_SETUP_PATH
call :ResolvePath pyperoot "..\..\"
set PYPE_SETUP_PATH=%pyperoot%
set PYTHONPATH=%PYPE_SETUP_PATH%;%PYTHONPATH%
echo [92m^>^>^>[0m Setting PYPE_ENV
set PYPE_ENV="C:\Users\Public\pype_env2"

call "docs\make.bat" clean
sphinx-apidoc -M -f -d 6 --ext-autodoc --ext-intersphinx --ext-viewcode -o docs\source pype %PYPE_SETUP_PATH%\repos\pype\pype\vendor\*
call "docs\make.bat" html
echo [92m^>^>^>[0m Doing cleanup ...
set PYTHONPATH=%_OLD_PYTHONPATH%
set PYPE_CONFIG=
call "C:\Users\Public\pype_env2\Scripts\deactivate.bat"
exit /b

:ResolvePath
    set %1=%~dpfn2
    exit /b
