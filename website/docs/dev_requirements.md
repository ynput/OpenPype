---
id: dev_requirements
title: Requirements
sidebar_label: Requirements
---


We aim to closely follow [**VFX Reference Platform**](https://vfxplatform.com/)

OpenPype is written in Python 3 with specific elements still running in Python2 until all DCCs are fully updated. To see the list of those, that are not quite there yet, go to [VFX Python3 tracker](https://vfxpy.com/)

The main things you will need to run and build pype are:

- **Terminal** in your OS
    - PowerShell 5.0+ (Windows)
    - Bash (Linux)
- [**Python 3.7.9**](#python) or higher
- [**MongoDB**](#database)


## OS

It can be built and ran on all common platforms. We develop and test on the following:

- **Windows** 10
- **Linux**
    - **Ubuntu** 20.04 LTS
    - **Centos** 7
- **Mac OSX** 
    - **10.15** Catalina
    - **11.1** Big Sur (using Rosetta2)


## Database 

Database version should be at least **MongoDB 4.4**.

Pype needs site-wide installation of **MongoDB**. It should be installed on
reliable server, that all workstations (and possibly render nodes) can connect. This
server holds **Avalon** database that is at the core of everything

Depending on project size and number of artists working connection speed and
latency influence performance experienced by artists. If remote working is required, this mongodb
server must be accessible from Internet or cloud solution can be used. Reasonable backup plan
or high availability options are recommended. *Replication* feature of MongoDB should be considered. This is beyond the
scope of this documentation, please refer to [MongoDB Documentation](https://docs.mongodb.com/manual/replication/).

Pype can run it's own instance of mongodb, mostly for testing and development purposes.
For that it uses locally installed MongoDB.

Download it from [mognoDB website](https://www.mongodb.com/download-center/community), install it and
add to the `PATH`. On Windows, Pype tries to find it in standard installation destination or using `PATH`.

To run mongoDB on server, use your server distribution tools to set it up (on Linux).

## Python

**Python 3.7.8** is the recommended version to use (as per [VFX platform CY2021](https://vfxplatform.com/)).

If you're planning to run openPYPE on workstations from built executables (highly recommended), you will only need python for building and development, however, if you'd like to run from source centrally, every user will need python installed. 

## Hardware

openPYPE should be installed on all workstations that need to use it, the same as any other application. 

There are no specific requirements for the hardware. If the workstation can run
the major DCCs, it most probably can run openPYPE.

Installed, it takes around 400MB of space, depending on the platform


For well functioning ftrack event server, we recommend a linux virtual server with Ubuntu or CentOS. CPU and RAM allocation needs differ based on the studio size, but a 2GB of ram, with a dual core CPU and around 4GB of storage should suffice


## Deployment

For pushing pipeline updates to the artists, you will need to create a shared folder that 
will be accessible with at least Read permission to every OpenPype user in the studio.
This can also be hosted on the cloud in fully distributed deployments.



## Dependencies

### Key projects we depend on

- [**Avalon**](https://github.com/getavalon)
- [**Pyblish**](https://github.com/pyblish)
- [**OpenTimelineIO**](https://github.com/PixarAnimationStudios/OpenTimelineIO)
- [**OpenImageIO**](https://github.com/OpenImageIO/oiio)
- [**FFmpeg**](https://github.com/FFmpeg/FFmpeg)


### Python modules we use and their licenses

|               Package               |                           License                            |
|-------------------------------------|--------------------------------------------------------------|
|              acre 1.0.0             |        GNU Lesser General Public License v3 (LGPLv3)         |
|            aiohttp 3.7.3            |                           Apache 2                           |
|       aiohttp-json-rpc 0.13.3       |                          Apache 2.0                          |
|            appdirs 1.4.4            |                             MIT                              |
|           blessed 1.17.12           |                             MIT                              |
|             click 7.1.2             |                         BSD-3-Clause                         |
|             clique 1.5.0            |                     Apache License (2.0)                     |
|            coverage 5.3.1           |                          Apache 2.0                          |
|           cx-Freeze 6.5.1           |              Python Software Foundation License              |
|            docutils 0.16            | public domain, Python, 2-Clause BSD, GPL 3 (see COPYING.txt) |
|             flake8 3.8.4            |                             MIT                              |
|       ftrack-python-api 2.0.0       |                     Apache License (2.0)                     |
|             jinxed 1.0.1            |                           MPLv2.0                            
|           log4mongo 1.7.0           |                             BSD                              |
|      OpenTimelineIO 0.14.0.dev1     |                 Modified Apache 2.0 License                  |
|             Pillow 8.1.0            |                             HPND                             |
|          pyblish-base 1.8.8         |                             LGPL                             |
|          pycodestyle 2.6.0          |                        Expat license                         |
|           pydocstyle 5.1.1          |                             MIT                              |
|             pylint 2.6.0            |                             GPL                              |
|            pymongo 3.11.2           |                 Apache License, Version 2.0                  |
|             pynput 1.7.2            |                            LGPLv3                            |
|             PyQt5 5.15.2            |                            GPL v3                            |
|             pytest 6.2.1            |                             MIT                              |
|          pytest-cov 2.11.0          |                             MIT                              |
|          pytest-print 0.2.1         |                             MIT                              |
|         pywin32-ctypes 0.2.0        |                             BSD                              |
|             Qt.py 1.3.2             |                             MIT                              |
|              six 1.15.0             |                             MIT                              |
|           speedcopy 2.1.0           |                           UNKNOWN                            |
|             Sphinx 3.4.3            |                             BSD                              |
|     sphinx-qt-documentation 0.3     |                         BSD-3-Clause                         |
|    sphinxcontrib-websupport 1.2.4   |                             BSD                              |
|             tqdm 4.56.0             |                    MPLv2.0, MIT Licences                     |
|             wheel 0.36.2            |                             MIT                              |
|         wsrpc-aiohttp 3.1.1         |                   Apache Software License                    |
