---
id: dev_build
title: Build OpenPYPE from source
sidebar_label: Build
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';


To build Pype you currently need (on all platforms):

- **[Python 3.7](https://www.python.org/downloads/)** as we are following [vfx platform](https://vfxplatform.com).
- **[git](https://git-scm.com/downloads)**

We use [CX_Freeze](https://cx-freeze.readthedocs.io/en/latest) to freeze the code and all dependencies.


<Tabs
  groupId="platforms"
  defaultValue="win"
  values={[
    {label: 'Windows', value: 'win'},
    {label: 'Linux', value: 'linux'},
    {label: 'Mac', value: 'mac'},
  ]}>

<TabItem value="win">

More tools might be needed for installing some dependencies (for example for **OpenTimelineIO**) - mostly
development tools like [CMake](https://cmake.org/) and [Visual Studio](https://visualstudio.microsoft.com/cs/downloads/)

### Clone repository:
```sh
git clone --recurse-submodules git@github.com:pypeclub/pype.git
```

### Run from source

For development purposes it is possible to run OpenPype directly from the source. We provide a simple launcher script for this. 

To start OpenPype from source you need to 

1) Run `.\tools\create_env.ps1` to create virtual environment in `.\venv`
2) Run `.\tools\run_tray.ps1` if you have all required dependencies on your machine you should be greeted with OpenPype igniter window and once you give it your Mongo URL, with OpenPype icon in the system tray.


### To build OpenPype:

1) Run `.\tools\create_env.ps1` to create virtual environment in `.\venv`
2) Run `.\tools\build.ps1` to build pype executables in `.\build\`

To create distributable OpenPype versions, run `./tools/create_zip.ps1` - that will
create zip file with name `pype-vx.x.x.zip` parsed from current pype repository and
copy it to user data dir. You can specify `--path /path/to/zip` to force it into a different 
location. This can be used to prepare new version releases for artists in the studio environment
without the need to re-build the whole package



</TabItem>
<TabItem value="linux">

#### Docker
You can use Docker to build OpenPype. Just run:
```sh
sudo ./tools/docker_build.sh
```
and you should have built OpenPype in `build` directory. It is using **Centos 7**
as a base image.

You can pull the image:

```sh
docker pull pypeclub/openpype:latest
```

#### Manual build
To build OpenPype on Linux you wil need:

- **[curl](https://curl.se)** on systems that doesn't have one preinstalled.
- Python header files installed (**python3-dev** on Ubuntu for example).
- **bzip2**, **readline**, **sqlite3** and other libraries.

Because some Linux distros come with newer Python version pre-installed, you might 
need to install **3.7** version and make use of it explicitly. 
Your best bet is probably using [pyenv](https://github.com/pyenv/pyenv).

You can use your package manager to install **git** and other packages to your build
environment.
Use curl for pyenv installation

:::note Install build requirements for **Ubuntu**

```sh
sudo apt-get update; sudo apt-get install --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git
```

In case you run in error about `xcb` when running Pype,
you'll need also additional libraries for Qt5:

```sh
sudo apt install qt5-default
```
:::

:::note Install build requirements for **Centos**

```sh
yum install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel git
```

In case you run in error about `xcb` when running Pype,
you'll need also additional libraries for Qt5:

```sh
sudo yum install qt5-qtbase-devel
```

:::

For more information about setting your build environmet please refer to [pyenv suggested build environment](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)

#### Common steps for all Distros

Use pyenv to prepare Python version for Pype build

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

# change path to pype 3
cd /path/to/pype-3

# set local python version
pyenv local 3.7.9

```

#### To build Pype:

1. Run `.\tools\create_env.sh` to create virtual environment in `.\venv`
2. Run `.\tools\build.sh` to build pype executables in `.\build\`

</TabItem>
<TabItem value="mac">

To build pype on MacOS you wil need:

- **[Homebrew](https://brew.sh)**, Easy way of installing everything necessary is to use.
- **[CMake](https://cmake.org/)** to build some external OpenPype dependencies.
- **XCode Command Line Tools** (or some other build system)

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
echo 'eval "$(pypenv init -)"' >> ~/.zshrc
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
# switch to Pype source directory
pyenv local 3.7.9
```

#### To build Pype:

1. Run `.\tools\create_env.sh` to create virtual environment in `.\venv`
2. Run `.\tools\build.sh` to build Pype executables in `.\build\`

</TabItem>
</Tabs>
