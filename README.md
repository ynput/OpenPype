
Pype
====

Introduction
------------

Multi-platform open-source pipeline built around the [Avalon](https://getavalon.github.io/) platform,
expanding it with extra features and integrations. Pype connects asset database, project management
and time tracking into a single modular system. It has tight integration
with [ftrack](https://www.ftrack.com/en/), but it can also run independently.

To get all the key information about the project, go to [PYPE.club](http://pype.club)

Requirements
------------
Pype will run on most typical hardware configurations commonly found in studios around the world.
It is installed on artist computer and can take up 3Gb of space depending on number of versions
and other dependencies. 

For well functioning [ftrack](https://www.ftrack.com/en/) event server, we recommend a 
linux virtual server with [Ubuntu](https://ubuntu.com/) or [CentosOS](https://www.centos.org/).
CPU and RAM allocation need differ based on the studio size, but a 2GB of RAM, with a
dual core CPU and around 4GB of storage should suffice.

Pype needs running [mongodb](https://www.mongodb.com/) server with good connectivity as it is
heavily used by Pype. Depending on project size and number of artists working connection speed and
latency influence performance experienced by artists. If remote working is required, this mongodb
server must be accessible from Internet or cloud solution can be used. Reasonable backup plan
or high availability options are recommended.

Building Pype
-------------

### Windows

You will need [Python 3.7 and newer](https://www.python.org/downloads/) and [git](https://git-scm.com/downloads).
More tools might be needed for installing dependencies (for example for **OpenTimelineIO**) - mostly
development tools like [CMake](https://cmake.org/) and [Visual Studio](https://visualstudio.microsoft.com/cs/downloads/)

Clone repository:
```sh
git clone --recurse-submodules git@github.com:pypeclub/pype.git
```

#### To build Pype:

1) Run `.\tools\create_env.ps1` to create virtual environment in `.\venv`
2) Run `.\tools\build.ps1` to build pype executables in `.\build\`

To create distributable Pype versions, run `./tools/create_zip.ps1` - that will
create zip file with name `pype-vx.x.x.zip` parsed from current pype repository and
copy it to user data dir, or you can specify `--path /path/to/zip` to force it there.

You can then point **Igniter** - Pype setup tool - to directory containing this zip and
it will install it on current computer.

Pype is build using [CX_Freeze](https://cx-freeze.readthedocs.io/en/latest) to freeze itself and all dependencies.

Running Pype
------------

Pype can by executed either from live sources (this repository) or from
*"frozen code"* - executables that can be build using steps described above.

If Pype is executed from live sources, it will use Pype version included in them. If
it is executed from frozen code it will try to find latest Pype version installed locally
on current computer and if it is not found, it will ask for its location. On that location
pype can be either in directories or zip files. Pype will try to find latest version and
install it to user data directory (on Windows to `%LOCALAPPDATA%\pypeclub\pype`).

### From sources
Pype can be run directly from sources by activating virtual environment:
```powershell
.\venv\Scripts\Activate.ps1
```
and running:
```powershell
python start.py tray
```
This will use current Pype version with sources. You can override this with `--use-version=x.x.x` and
then Pype will try to find locally installed specified version (present in user data directory).

### From frozen code

You need to build Pype first. This will produce two executables - `pype.exe` and `pype_console.exe`.
First one will act as GUI application and will not create console (useful in production environments).
The second one will create console and will write output there - useful for headless application and
debugging purposes. If you need pype version installed, just run `./tools/create_zip.ps1` without
arguments and it will create zip file that pype can use.


Building documentation
----------------------

Top build API documentation, run `.\tools\make_docs.ps1`. It will create html documentation
from current sources in `.\docs\build`.

**Note that it needs existing virtual environment.**

Running tests
-------------

To run tests, execute `.\tools\run_tests.ps1`.

**Note that it needs existing virtual environment.**