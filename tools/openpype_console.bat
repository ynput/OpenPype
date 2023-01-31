cd "%~dp0\.."
echo %OPENPYPE_MONGO%
.poetry\bin\poetry.exe run python start.py %*
