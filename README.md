
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-25-orange.svg?style=flat-square)](#contributors-)
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
    <td align="center"><a href="http://pype.club/"><img src="https://avatars.githubusercontent.com/u/3333008?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Milan Kolar</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=mkolar" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=mkolar" title="Documentation">📖</a> <a href="#infra-mkolar" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#business-mkolar" title="Business development">💼</a> <a href="#content-mkolar" title="Content">🖋</a> <a href="#fundingFinding-mkolar" title="Funding Finding">🔍</a> <a href="#maintenance-mkolar" title="Maintenance">🚧</a> <a href="#projectManagement-mkolar" title="Project Management">📆</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Amkolar" title="Reviewed Pull Requests">👀</a> <a href="#mentoring-mkolar" title="Mentoring">🧑‍🏫</a> <a href="#question-mkolar" title="Answering Questions">💬</a></td>
    <td align="center"><a href="https://www.linkedin.com/in/jakubjezek79"><img src="https://avatars.githubusercontent.com/u/40640033?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Jakub Ježek</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=jakubjezek001" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=jakubjezek001" title="Documentation">📖</a> <a href="#infra-jakubjezek001" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#content-jakubjezek001" title="Content">🖋</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Ajakubjezek001" title="Reviewed Pull Requests">👀</a> <a href="#maintenance-jakubjezek001" title="Maintenance">🚧</a> <a href="#mentoring-jakubjezek001" title="Mentoring">🧑‍🏫</a> <a href="#projectManagement-jakubjezek001" title="Project Management">📆</a> <a href="#question-jakubjezek001" title="Answering Questions">💬</a></td>
    <td align="center"><a href="https://github.com/antirotor"><img src="https://avatars.githubusercontent.com/u/33513211?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Ondřej Samohel</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=antirotor" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=antirotor" title="Documentation">📖</a> <a href="#infra-antirotor" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#content-antirotor" title="Content">🖋</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Aantirotor" title="Reviewed Pull Requests">👀</a> <a href="#maintenance-antirotor" title="Maintenance">🚧</a> <a href="#mentoring-antirotor" title="Mentoring">🧑‍🏫</a> <a href="#projectManagement-antirotor" title="Project Management">📆</a> <a href="#question-antirotor" title="Answering Questions">💬</a></td>
    <td align="center"><a href="https://github.com/iLLiCiTiT"><img src="https://avatars.githubusercontent.com/u/43494761?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Jakub Trllo</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=iLLiCiTiT" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=iLLiCiTiT" title="Documentation">📖</a> <a href="#infra-iLLiCiTiT" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3AiLLiCiTiT" title="Reviewed Pull Requests">👀</a> <a href="#maintenance-iLLiCiTiT" title="Maintenance">🚧</a> <a href="#question-iLLiCiTiT" title="Answering Questions">💬</a></td>
    <td align="center"><a href="https://github.com/kalisp"><img src="https://avatars.githubusercontent.com/u/4457962?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Petr Kalis</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=kalisp" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=kalisp" title="Documentation">📖</a> <a href="#infra-kalisp" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Akalisp" title="Reviewed Pull Requests">👀</a> <a href="#maintenance-kalisp" title="Maintenance">🚧</a> <a href="#question-kalisp" title="Answering Questions">💬</a></td>
    <td align="center"><a href="https://github.com/64qam"><img src="https://avatars.githubusercontent.com/u/26925793?v=4?s=80" width="80px;" alt=""/><br /><sub><b>64qam</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=64qam" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3A64qam" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=64qam" title="Documentation">📖</a> <a href="#infra-64qam" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#projectManagement-64qam" title="Project Management">📆</a> <a href="#maintenance-64qam" title="Maintenance">🚧</a> <a href="#content-64qam" title="Content">🖋</a> <a href="#userTesting-64qam" title="User Testing">📓</a></td>
    <td align="center"><a href="http://www.colorbleed.nl/"><img src="https://avatars.githubusercontent.com/u/2439881?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Roy Nieterau</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=BigRoy" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=BigRoy" title="Documentation">📖</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3ABigRoy" title="Reviewed Pull Requests">👀</a> <a href="#mentoring-BigRoy" title="Mentoring">🧑‍🏫</a> <a href="#question-BigRoy" title="Answering Questions">💬</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/tokejepsen"><img src="https://avatars.githubusercontent.com/u/1860085?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Toke Jepsen</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=tokejepsen" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=tokejepsen" title="Documentation">📖</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Atokejepsen" title="Reviewed Pull Requests">👀</a> <a href="#mentoring-tokejepsen" title="Mentoring">🧑‍🏫</a> <a href="#question-tokejepsen" title="Answering Questions">💬</a></td>
    <td align="center"><a href="https://github.com/jrsndl"><img src="https://avatars.githubusercontent.com/u/45896205?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Jiri Sindelar</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=jrsndl" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Ajrsndl" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=jrsndl" title="Documentation">📖</a> <a href="#content-jrsndl" title="Content">🖋</a> <a href="#tutorial-jrsndl" title="Tutorials">✅</a> <a href="#userTesting-jrsndl" title="User Testing">📓</a></td>
    <td align="center"><a href="https://barbierisimone.com/"><img src="https://avatars.githubusercontent.com/u/1087869?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Simone Barbieri</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=simonebarbieri" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=simonebarbieri" title="Documentation">📖</a></td>
    <td align="center"><a href="http://karimmozilla.xyz/"><img src="https://avatars.githubusercontent.com/u/82811760?v=4?s=80" width="80px;" alt=""/><br /><sub><b>karimmozilla</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=karimmozilla" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/Allan-I"><img src="https://avatars.githubusercontent.com/u/76656700?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Allan I. A.</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=Allan-I" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/aardschok"><img src="https://avatars.githubusercontent.com/u/26920875?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Wijnand Koreman</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=aardschok" title="Code">💻</a></td>
    <td align="center"><a href="http://jedimaster.cnblogs.com/"><img src="https://avatars.githubusercontent.com/u/1798206?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Bo Zhou</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=zhoub" title="Code">💻</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://www.linkedin.com/in/clementhector/"><img src="https://avatars.githubusercontent.com/u/7068597?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Clément Hector</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=ClementHector" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3AClementHector" title="Reviewed Pull Requests">👀</a></td>
    <td align="center"><a href="https://twitter.com/davidlatwe"><img src="https://avatars.githubusercontent.com/u/3357009?v=4?s=80" width="80px;" alt=""/><br /><sub><b>David Lai</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=davidlatwe" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3Adavidlatwe" title="Reviewed Pull Requests">👀</a></td>
    <td align="center"><a href="https://github.com/2-REC"><img src="https://avatars.githubusercontent.com/u/42170307?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Derek </b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=2-REC" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/pulls?q=is%3Apr+reviewed-by%3A2-REC" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=2-REC" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/gabormarinov"><img src="https://avatars.githubusercontent.com/u/8620515?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Gábor Marinov</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=gabormarinov" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=gabormarinov" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/icyvapor"><img src="https://avatars.githubusercontent.com/u/1195278?v=4?s=80" width="80px;" alt=""/><br /><sub><b>icyvapor</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=icyvapor" title="Code">💻</a> <a href="https://github.com/pypeclub/OpenPype/commits?author=icyvapor" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/jlorrain"><img src="https://avatars.githubusercontent.com/u/7955673?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Jérôme LORRAIN</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=jlorrain" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/dmo-j-cube"><img src="https://avatars.githubusercontent.com/u/89823400?v=4?s=80" width="80px;" alt=""/><br /><sub><b>David Morris-Oliveros</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=dmo-j-cube" title="Code">💻</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/BenoitConnan"><img src="https://avatars.githubusercontent.com/u/82808268?v=4?s=80" width="80px;" alt=""/><br /><sub><b>BenoitConnan</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=BenoitConnan" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/Malthaldar"><img src="https://avatars.githubusercontent.com/u/33671694?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Malthaldar</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=Malthaldar" title="Code">💻</a></td>
    <td align="center"><a href="http://www.svenneve.com/"><img src="https://avatars.githubusercontent.com/u/2472863?v=4?s=80" width="80px;" alt=""/><br /><sub><b>Sven Neve</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=svenneve" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/zafrs"><img src="https://avatars.githubusercontent.com/u/26890002?v=4?s=80" width="80px;" alt=""/><br /><sub><b>zafrs</b></sub></a><br /><a href="https://github.com/pypeclub/OpenPype/commits?author=zafrs" title="Code">💻</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!