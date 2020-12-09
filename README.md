# Pype

## Introduction

Multi-platform open-source pipeline built around the [Avalon](https://getavalon.github.io/) platform, expanding it with extra features and integrations. Pype connects asset database, project management and time tracking into a single modular system. It has tight integration with [ftrack](https://www.ftrack.com/en/), but it can also run independently.

To get all the key information about the project, go to [PYPE.club](http://pype.club)

## Hardware requirements

Pype should be installed centrally on a fast network storage with at least read access right for all workstations and users in the Studio. Full Deplyoyment with all dependencies and both Development and Production branches installed takes about 1GB of data, however to ensure smooth updates and general working comfort, we recommend allocating at least at least 4GB of storage dedicated to PYPE deployment.

For well functioning [ftrack](https://www.ftrack.com/en/) event server, we recommend a linux virtual server with [Ubuntu](https://ubuntu.com/) or [CentosOS](https://www.centos.org/). CPU and RAM allocation need differ based on the studio size, but a 2GB of RAM, with a dual core CPU and around 4GB of storage should suffice.

## Building Pype

### Windows

You will need [Python 3.7 and newer](https://www.python.org/downloads/) and [git](https://git-scm.com/downloads).

Clone repository:
```sh
git clone --recurse-submodules git@github.com:pypeclub/pype.git
```

Run PowerShell script `build.ps1`. It will create *venv*, install all
required dependencies and build Pype. After it is finished, you will find
Pype in `build` folder.

You might need more tools for installing dependencies (for example for **OpenTimelineIO**) - mostly
development tools like [CMake](https://cmake.org/) and [Visual Studio](https://visualstudio.microsoft.com/cs/downloads/)

Pype is build using [CX_Freeze](https://cx-freeze.readthedocs.io/en/latest) to freeze itself and all dependencies.
