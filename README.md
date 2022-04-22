
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
OpenPype
====

[![documentation](https://github.com/pypeclub/pype/actions/workflows/documentation.yml/badge.svg)](https://github.com/pypeclub/pype/actions/workflows/documentation.yml) ![GitHub VFX Platform](https://img.shields.io/badge/vfx%20platform-2021-lightgrey?labelColor=303846)



Introduction
------------

Open-source pipeline for visual effects and animation built on top of the [Avalon](https://getavalon.github.io/) framework, expanding it with extra features and integrations. OpenPype connects your DCCs, asset database, project management and time tracking into a single system. It has a tight integration with [ftrack](https://www.ftrack.com/en/), but can also run independently or be integrated into a different project management solution.

OpenPype provides a robust platform for your studio, without the worry of a vendor lock. You will always have full access to the source-code and your project database will run locally or in the cloud of your choice.


To get all the information about the project, go to [OpenPype.io](http://openpype.io)

Requirements
------------

We aim to closely follow [**VFX Reference Platform**](https://vfxplatform.com/)

OpenPype is written in Python 3 with specific elements still running in Python2 until all DCCs are fully updated. To see the list of those, that are not quite there yet, go to [VFX Python3 tracker](https://vfxpy.com/)

The main things you will need to run and build OpenPype are:

- **Terminal** in your OS
    - PowerShell 5.0+ (Windows)
    - Bash (Linux)
- [**Python 3.7.8**](#python) or higher
- [**MongoDB**](#database) (needed only for local development)


It can be built and ran on all common platforms. We develop and test on the following:

- **Windows** 10
- **Linux**
    - **Ubuntu** 20.04 LTS
    - **Centos** 7
- **Mac OSX** 
    - **10.15** Catalina
    - **11.1** Big Sur (using Rosetta2)

For more details on requirements visit [requirements documentation](https://openpype.io/docs/dev_requirements)

Building OpenPype
-------------

To build OpenPype you currently need [Python 3.7](https://www.python.org/downloads/) as we are following
[vfx platform](https://vfxplatform.com). Because of some Linux distros comes with newer Python version
already, you need to install **3.7** version and make use of it. You can use perhaps [pyenv](https://github.com/pyenv/pyenv) for this on Linux.

### Windows

You will need [Python 3.7](https://www.python.org/downloads/) and [git](https://git-scm.com/downloads).
More tools might be needed for installing dependencies (for example for **OpenTimelineIO**) - mostly
development tools like [CMake](https://cmake.org/) and [Visual Studio](https://visualstudio.microsoft.com/cs/downloads/)

#### Clone repository:
```sh
git clone --recurse-submodules git@github.com:Pypeclub/OpenPype.git
```

#### To build OpenPype:

1) Run `.\tools\create_env.ps1` to create virtual environment in `.\venv`
2) Run `.\tools\fetch_thirdparty_libs.ps1` to download third-party dependencies like ffmpeg and oiio. Those will be included in build.
3) Run `.\tools\build.ps1` to build OpenPype executables in `.\build\`

To create distributable OpenPype versions, run `./tools/create_zip.ps1` - that will
create zip file with name `openpype-vx.x.x.zip` parsed from current OpenPype repository and
copy it to user data dir, or you can specify `--path /path/to/zip` to force it there.

You can then point **Igniter** - OpenPype setup tool - to directory containing this zip and
it will install it on current computer.

OpenPype is build using [CX_Freeze](https://cx-freeze.readthedocs.io/en/latest) to freeze itself and all dependencies.

### macOS

You will need [Python 3.7](https://www.python.org/downloads/) and [git](https://git-scm.com/downloads). You'll need also other tools to build
some OpenPype dependencies like [CMake](https://cmake.org/) and **XCode Command Line Tools** (or some other build system).

Easy way of installing everything necessary is to use [Homebrew](https://brew.sh):

1) Install **Homebrew**:
```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2) Install **cmake**:
```sh
brew install cmake
```

3) Install [pyenv](https://github.com/pyenv/pyenv):
```sh
brew install pyenv
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
pyenv init
exec "$SHELL"
PATH=$(pyenv root)/shims:$PATH
```

4) Pull in required Python version 3.7.x
```sh
# install Python build dependences
brew install openssl readline sqlite3 xz zlib

# replace with up-to-date 3.7.x version
pyenv install 3.7.9
```

5) Set local Python version
```sh
# switch to OpenPype source directory
pyenv local 3.7.9
```

#### To build OpenPype:

1) Run `.\tools\create_env.sh` to create virtual environment in `.\venv`
2) Run `.\tools\fetch_thirdparty_libs.sh` to download third-party dependencies like ffmpeg and oiio. Those will be included in build.
3) Run `.\tools\build.sh` to build OpenPype executables in `.\build\`

### Linux

#### Docker
Easiest way to build OpenPype on Linux is using [Docker](https://www.docker.com/). Just run:

```sh
sudo ./tools/docker_build.sh
```

This will by default use Debian as base image. If you need to make Centos 7 compatible build, please run:

```sh
sudo ./tools/docker_build.sh centos7
```

If all is successful, you'll find built OpenPype in `./build/` folder.

#### Manual build
You will need [Python 3.7](https://www.python.org/downloads/) and [git](https://git-scm.com/downloads). You'll also need [curl](https://curl.se) on systems that doesn't have one preinstalled.

To build Python related stuff, you need Python header files installed (`python3-dev` on Ubuntu for example).

You'll need also other tools to build
some OpenPype dependencies like [CMake](https://cmake.org/). Python 3 should be part of all modern distributions. You can use your package manager to install **git** and **cmake**.

<details>
<summary>Details for Ubuntu</summary>
Install git, cmake and curl

```sh
sudo apt install build-essential checkinstall
sudo apt install git cmake curl
```
#### Note:
In case you run in error about `xcb` when running OpenPype,
you'll need also additional libraries for Qt5:

```sh
sudo apt install qt5-default
```
or if you are on Ubuntu > 20.04, there is no `qt5-default` packages so you need to install its content individually:

```sh
sudo apt-get install qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools
```
</details>

<details>
<summary>Details for Centos</summary>
Install git, cmake and curl

```sh
sudo yum install qit cmake
```

#### Note:
In case you run in error about `xcb` when running OpenPype,
you'll need also additional libraries for Qt5:

```sh
sudo yum install qt5-qtbase-devel
```
</details>

<details>
<summary>Use pyenv to install Python version for OpenPype build</summary>

You will need **bzip2**, **readline**, **sqlite3** and other libraries.

For more details about Python build environments see:

https://github.com/pyenv/pyenv/wiki#suggested-build-environment

**For Ubuntu:**
```sh
sudo apt-get update; sudo apt-get install --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

**For Centos:**
```sh
yum install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel
```

**install pyenv**
```sh
curl https://pyenv.run | bash

# you can add those to ~/.bashrc
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# reload shell
exec $SHELL

# install Python 3.7.9
pyenv install -v 3.7.9

# change path to OpenPype 3
cd /path/to/openpype-3

# set local python version
pyenv local 3.7.9

```
</details>

#### To build OpenPype:

1) Run `.\tools\create_env.sh` to create virtual environment in `.\venv`
2) Run `.\tools\build.sh` to build OpenPype executables in `.\build\`


Running OpenPype
------------

OpenPype can by executed either from live sources (this repository) or from
*"frozen code"* - executables that can be build using steps described above.

If OpenPype is executed from live sources, it will use OpenPype version included in them. If
it is executed from frozen code it will try to find latest OpenPype version installed locally
on current computer and if it is not found, it will ask for its location. On that location
OpenPype can be either in directories or zip files. OpenPype will try to find latest version and
install it to user data directory (on Windows to `%LOCALAPPDATA%\pypeclub\openpype`, on Linux
`~/.local/share/openpype` and on macOS in `~/Library/Application Support/openpype`).

### From sources
OpenPype can be run directly from sources by activating virtual environment:

```sh
poetry run python start.py tray
```

This will use current OpenPype version with sources. You can override this with `--use-version=x.x.x` and
then OpenPype will try to find locally installed specified version (present in user data directory).

### From frozen code

You need to build OpenPype first. This will produce two executables - `openpype_gui(.exe)` and `openpype_console(.exe)`.
First one will act as GUI application and will not create console (useful in production environments).
The second one will create console and will write output there - useful for headless application and
debugging purposes. If you need OpenPype version installed, just run `./tools/create_zip(.ps1|.sh)` without
arguments and it will create zip file that OpenPype can use.


Building documentation
----------------------

Top build API documentation, run `.\tools\make_docs(.ps1|.sh)`. It will create html documentation
from current sources in `.\docs\build`.

**Note that it needs existing virtual environment.**

Running tests
-------------

To run tests, execute `.\tools\run_tests(.ps1|.sh)`.

**Note that it needs existing virtual environment.**

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="http://pype.club/"><img src="https://avatars.githubusercontent.com/u/3333008?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Milan Kolar</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=mkolar" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=mkolar" title="Documentation">📖</a> <a href="#infra-mkolar" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!