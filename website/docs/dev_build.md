---
id: dev_build
title: Build OpenPYPE from source
sidebar_label: Build
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## Introduction

To build Pype you currently need (on all platforms):

- **[Python 3.7](https://www.python.org/downloads/)** as we are following [vfx platform](https://vfxplatform.com).
- **[git](https://git-scm.com/downloads)**

We use [CX_Freeze](https://cx-freeze.readthedocs.io/en/latest) to freeze the code and all dependencies and
[Poetry](https://python-poetry.org/) for virtual environment management.

This is outline of build steps. Most of them are done automatically via scripts:
- Virtual environment is created using **Poetry** in `.venv`
- Necessary python modules outside of `.venv` are stored to `./vendor/python` (like `PySide2`)
- Necessary third-party tools (like [ffmpeg](https://www.ffmpeg.org/), [OpenImageIO](https://github.com/OpenImageIO/oiio)
  and [usd libraries](https://developer.nvidia.com/usd)) are downloaded to `./vendor/bin`
- OpenPype code is frozen with **cx_freeze** to `./build`
- Modules are moved from `lib` to `dependencies` to solve some Python 2 / Python 3 clashes
- On Mac application bundle and dmg image will be created from built code.
- On Windows, you can create executable installer with `./tools/build_win_installer.ps1`

### Clone OpenPype repository:
```powershell
git clone --recurse-submodules https://github.com/pypeclub/OpenPype.git
```

## Platform specific steps

<Tabs
  groupId="platforms"
  defaultValue="win"
  values={[
    {label: 'Windows', value: 'win'},
    {label: 'Linux', value: 'linux'},
    {label: 'Mac', value: 'mac'},
  ]}>

<TabItem value="win">

### Windows
More tools might be needed for installing some dependencies (for example for **OpenTimelineIO**) - mostly
development tools like [CMake](https://cmake.org/) and [Visual Studio](https://visualstudio.microsoft.com/cs/downloads/)

#### Run from source

For development purposes it is possible to run OpenPype directly from the source. We provide a simple launcher script for this. 

To start OpenPype from source you need to 

1. Run `.\tools\create_env.ps1` to create virtual environment in `.venv`
2. Run `.\tools\fetch_thirdparty_libs.ps1` to get **PySide2**, **ffmpeg**, **oiio** and other tools needed.
3. Run `.\tools\run_tray.ps1` if you have all required dependencies on your machine you should be greeted with OpenPype igniter window and once you give it your Mongo URL, with OpenPype icon in the system tray.

Step 1 and 2 needs to be run only once (or when something was changed).

#### To build OpenPype:
1. Run `.\tools\create_env.ps1` to create virtual environment in `.venv`
2. Run `.\tools\fetch_thirdparty_libs.ps1` to get **PySide2**, **ffmpeg**, **oiio** and other tools needed.
3. `.\tools\build.ps1` to build OpenPype to `.\build`


To create distributable OpenPype versions, run `.\tools\create_zip.ps1` - that will
create zip file with name `pype-vx.x.x.zip` parsed from current pype repository and
copy it to user data dir. You can specify `--path \path\to\zip` to force it into a different 
location. This can be used to prepare new version releases for artists in the studio environment
without the need to re-build the whole package



</TabItem>
<TabItem value="linux">

### Linux

#### Docker
You can use Docker to build OpenPype. Just run:
```shell
$ sudo ./tools/docker_build.sh
```

This will by default use Debian as base image. If you need to make Centos 7 compatible build, please run:

```sh
sudo ./tools/docker_build.sh centos7
```

and you should have built OpenPype in `build` directory. It is using **Centos 7**
as a base image.

You can pull the image:

```shell
# replace 3.0.0 tag with version you want
$ docker pull pypeclub/openpype:3.0.0
```
See https://hub.docker.com/r/pypeclub/openpype/tag for more.

Beware that as Python is built against some libraries version in Centos 7 base image,
those might not be available in linux version you are using. We try to handle those we
found (libffi, libcrypto/ssl, etc.) but there might be more.

#### Manual build

To build OpenPype on Linux you will need:

- **[curl](https://curl.se)** on systems that doesn't have one preinstalled.
- **bzip2**, **readline**, **sqlite3** and other libraries.

Because some Linux distros come with newer Python version pre-installed, you might 
need to install **3.7** version and make use of it explicitly. 
Your best bet is probably using [pyenv](https://github.com/pyenv/pyenv).

You can use your package manager to install **git** and other packages to your build
environment.

#### Common steps for all Distros

Use pyenv to prepare Python version for Pype build

```shell
$ curl https://pyenv.run | bash

# you can add those to ~/.bashrc
$ export PATH="$HOME/.pyenv/bin:$PATH"
$ eval "$(pyenv init -)"
$ eval "$(pyenv virtualenv-init -)"

# reload shell
$ exec $SHELL

# install Python 3.7.10
# python will be downloaded and build so please make sure
# you have all necessary requirements installed (see below).
$ pyenv install -v 3.7.10

# change path to pype 3
$ cd /path/to/pype-3

# set local python version
$ pyenv local 3.7.10
```
:::note Install build requirements for **Ubuntu**

```shell
sudo apt-get update; sudo apt-get install --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git patchelf
```

In case you run in error about `xcb` when running Pype,
you'll need also additional libraries for Qt5:

```shell
sudo apt install qt5-default
```
:::

:::note Install build requirements for **Centos 7**

```shell
$ sudo yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
$ sudo yum install centos-release-scl
$ sudo yum install bash which git devtoolset-7-gcc* \
        make cmake curl wget gcc zlib-devel bzip2 \
        bzip2-devel readline-devel sqlite sqlite-devel \
        openssl-devel tk-devel libffi-devel qt5-qtbase-devel \
        patchelf
```
:::

:::note Install build requirements for other distros

Build process usually needs some reasonably recent versions of libraries and tools. You
can follow what's needed for Ubuntu and change it for your package manager. Centos 7 steps
have additional magic to overcame very old versions.
:::

For more information about setting your build environment please refer to [pyenv suggested build environment](https://github.com/pyenv/pyenv/wiki#suggested-build-environment).


#### To build Pype:
1. Run `./tools/create_env.sh` to create virtual environment in `./venv`
2. Run `./tools/fetch_thirdparty_libs.sh` to get **PySide2**, **ffmpeg**, **oiio** and other tools needed.
3. Run `./tools/build.sh` to build pype executables in `.\build\`

</TabItem>
<TabItem value="mac">

### MacOS
To build pype on MacOS you will need:

- **[Homebrew](https://brew.sh)** - easy way of installing everything necessary.
- **[CMake](https://cmake.org/)** to build some external OpenPype dependencies.
- **XCode Command Line Tools** (or some other build system)
- **[create-dmg](https://formulae.brew.sh/formula/create-dmg)** to create dmg image from application
bundle.

1) Install **Homebrew**:
```shell
$ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2) Install **cmake**:
```shell
$ brew install cmake
```

3) Install [pyenv](https://github.com/pyenv/pyenv):
```shell
$ brew install pyenv
$ echo 'eval "$(pypenv init -)"' >> ~/.zshrc
$ pyenv init
$ exec "$SHELL"
$ PATH=$(pyenv root)/shims:$PATH
```

4) Pull in required Python version 3.7.x
```shell
# install Python build dependences
$ brew install openssl readline sqlite3 xz zlib

# replace with up-to-date 3.7.x version
$ pyenv install 3.7.9
```

5) Set local Python version
```shell
# switch to Pype source directory
$ pyenv local 3.7.9
```

6) Install `create-dmg`
```shell
$ brew install create-dmg
```

#### To build Pype:

1. Run `./tools/create_env.sh` to create virtual environment in `./venv`.
2. Run `./tools/fetch_thirdparty_libs.sh` to get **ffmpeg**, **oiio** and other tools needed.
3. Run `./tools/build.sh` to build OpenPype Application bundle in `./build/`.

</TabItem>
</Tabs>

## Adding dependencies
### Python modules
If you are extending OpenPype and you need some new modules not included, you can add them
to `pyproject.toml` to `[tool.poetry.dependencies]` section.

```toml title="/pyproject.toml"
[tool.poetry.dependencies]
python = "3.7.*"
aiohttp = "^3.7"
aiohttp_json_rpc = "*" # TVPaint server
acre = { git = "https://github.com/pypeclub/acre.git" }
opentimelineio = { version = "0.14.0.dev1", source = "openpype" }
#...
```
It is useful to add comment to it so others can see why this was added and where it is used.
As you can see you can add git repositories or custom wheels (those must be
added to `[[tool.poetry.source]]` section).

To add something only for specific platform, you can use markers like:
```toml title="Install pywin32 only on Windows"
pywin32 = { version = "300", markers = "sys_platform == 'win32'" }
```

For more information see [Poetry documentation](https://python-poetry.org/docs/dependency-specification/).

### Python modules as thirdparty
There are some python modules that can be available only in OpenPype and should not be propagated to any subprocess.
Best example is **PySide2** which is required to run OpenPype but can be used only in OpenPype and should not be in PYTHONPATH for most of host applications.
We've decided to separate these breaking dependencies to be able run OpenPype from code and from build the same way.

:::warning
**PySide2** has handled special cases related to it's build process.
### Linux
- We're fixing rpath of shared objects on linux which is modified during cx freeze processing.
### MacOS
- **QtSql** libraries are removed on MacOS because their dependencies are not available and would require to modify rpath of Postgre library.
:::

### Binary dependencies
To add some binary tool or something that doesn't fit standard Python distribution methods, you
can use [fetch_thirdparty_libs](#fetch_thirdparty_libs) script. It will take things defined in
`pyproject.toml` under `[openpype]` section like this:

```toml title="/pyproject.toml"
[openpype]

[openpype.thirdparty.ffmpeg.windows]
url = "https://distribute.openpype.io/thirdparty/ffmpeg-4.4-windows.zip"
hash = "dd51ba29d64ee238e7c4c3c7301b19754c3f0ee2e2a729c20a0e2789e72db925"
# ...
```
This defines FFMpeg for Windows. It will be downloaded from specified url, its checksum will
be validated (it's sha256) and it will be extracted to `/vendor/bin/ffmpeg/windows` (partly taken
from its section name).

## Script tools
(replace extension with the one for your system - `ps1` for windows, `sh` for linux/macos)

### build
This will build OpenPype to `build` directory. If virtual environment is not created yet, it will
install [Poetry](https://python-poetry.org/) and using it download and install necessary
packages needed for build. It is recommended that you run [fetch_thirdparty_libs](#fetch_thirdparty_libs)
to download FFMpeg, OpenImageIO and others that are needed by OpenPype and are copied during the build.

#### Arguments
`--no-submodule-update` - to disable updating submodules. This allows to make custom-builds for testing
feature changes in submodules.

### build_win_installer
This will take already existing build in `build` directory and create executable installer using
[Inno Setup](https://jrsoftware.org/isinfo.php) and definitions in `./inno_setup.iss`. You need OpenPype
build using [build script](#build), Inno Setup installed and in PATH before running this script.

:::note
Windows only
:::

### create_env
Script to create virtual environment for build and running OpenPype from sources. It is using
[Poetry](https://python-poetry.org/). All dependencies are defined in `pyproject.toml`, resolved by
Poetry into `poetry.lock` file and then installed. Running this script without Poetry will download
it, install it to `.poetry` and then install virtual environment from `poetry.lock` file. If you want
to update packages version, just run `poetry update` or delete lock file.

#### Arguments
`--verbose` - to increase verbosity of Poetry. This can be useful for debugging package conflicts.

### create_zip
Script to create packaged OpenPype version from current sources. This will strip developer stuff and
package it into zip that can be used for [auto-updates for studio wide distributions](admin_distribute.md#automatic-updates), etc.
Same as:
```shell
poetry run python ./tools/create_zip.py
```

### docker_build.sh *[variant]*
Script to build OpenPype on [Docker](https://www.docker.com/) enabled systems - usually Linux and Windows
with [Docker Desktop](https://docs.docker.com/docker-for-windows/install/)
and [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/about) (WSL) installed.

It must be run with administrative privileges - `sudo ./docker_build.sh`.

It will use latest **Debian** base image to build OpenPype. If you need to build OpenPype for
older systems like Centos 7, use `centos7` as argument. This will use another Dockerfile to build
OpenPype with **Centos 7** as base image.

You'll see your build in `./build` folder.

### fetch_thirdparty_libs
This script will download necessary tools for OpenPype defined in `pyproject.toml` like FFMpeg,
OpenImageIO and USD libraries and put them to `./vendor/bin`. Those are then included in build.
Running it will overwrite everything on their respective paths.
Same as:
```shell
poetry run python ./tools/fetch_thirdparty_libs.py
```

### make_docs
Script will run [sphinx](https://www.sphinx-doc.org/) to build api documentation in html. You
should see it then under `./docs/build/html`.

### run_documentation
This will start up [Docusaurus](https://docusaurus.io/) to display OpenPype user documentation.
Useful for offline browsing or editing documentation itself. You will need [Node.js](https://nodejs.org/)
and [Yarn](https://yarnpkg.com/) to run this script. After executing it, you'll see new
browser window with current OpenPype documentation.
Same as:
```shell
cd ./website
yarn start
```

### run_mongo
Helper script to run local mongoDB server for development and testing. You will need
[mongoDB server](https://www.mongodb.com/try/download/community) installed in standard location
or in PATH (standard location works only on Windows). It will start by default on port `2707` and
it will put its db files to `../mongo_db_data` relative to OpenPype sources.

### run_project_manager
Helper script to start OpenPype Project Manager tool.
Same as:
```shell
poetry run python start.py projectmanager
```

### run_settings
Helper script to open OpenPype Settings UI.
Same as:
```shell
poetry run python start.py settings --dev
```

### run_tests
Runs OpenPype test suite.

### run_tray
Helper script to run OpenPype Tray.
Same as:
```shell
poetry run python start.py tray
```

### update_submodules
Helper script to update OpenPype git submodules.
Same as:
```shell
git submodule update --recursive --remote
```
