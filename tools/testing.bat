goto comment
SYNOPSIS
  Helper script running scripts through the OpenPype environment.

DESCRIPTION
  This script is usually used as a replacement for building when tested farm integration like Deadline.

EXAMPLE

cmd> .\openpype_console.bat path/to/python_script.py
:comment

cd "%~dp0"
set OPENPYPE_MONGO=mongodb://localhost:2707/
openpype_console runtests C:\Users\tokejepsen\OpenPype\tests\integration\hosts\maya\test_publish_in_maya.py --mongo_url "mongodb://localhost:2707/"
