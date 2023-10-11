---
id: admin_hosts_resolve
title: DaVinci Resolve Setup
sidebar_label: DaVinci Resolve
---

:::warning
Only Resolve Studio is supported due to Python API limitation in Resolve (free).
:::

## Resolve requirements
Due to the way resolve handles python and python scripts there are a few steps required steps needed to be done on any machine that will be using OpenPype with resolve.

## Basic setup

-   Supported version is up to v18
-   Install Python 3.6.2 (latest tested v17) or up to 3.9.13 (latest tested on v18)
-   pip install PySide2:
    -   Python 3.9.*: open terminal and go to python.exe directory, then `python -m pip install PySide2`
-   pip install OpenTimelineIO:
    -   Python 3.9.*: open terminal and go to python.exe directory, then  `python -m pip install OpenTimelineIO`
    -   Python 3.6: open terminal and go to python.exe directory, then `python -m pip install git+https://github.com/PixarAnimationStudios/OpenTimelineIO.git@5aa24fbe89d615448876948fe4b4900455c9a3e8` and move built files from `./Lib/site-packages/opentimelineio/cxx-libs/bin and lib` to `./Lib/site-packages/opentimelineio/`. I was building it on Win10 machine with Visual Studio Community 2019 and
    ![image](https://user-images.githubusercontent.com/40640033/102792588-ffcb1c80-43a8-11eb-9c6b-bf2114ed578e.png) with installed CMake in PATH.
-   make sure Resolve Fusion (Fusion Tab/menu/Fusion/Fusion Settings) is set to Python 3.6
    ![image](https://user-images.githubusercontent.com/40640033/102631545-280b0f00-414e-11eb-89fc-98ac268d209d.png)
-   Open OpenPype **Tray/Admin/Studio settings** > `applications/resolve/environment` and add Python3 path to `RESOLVE_PYTHON3_HOME` platform related.

## Editorial setup

This is how it looks on my testing project timeline
![image](https://user-images.githubusercontent.com/40640033/102637638-96ec6600-4156-11eb-9656-6e8e3ce4baf8.png)
Notice I had renamed tracks to `main` (holding metadata markers) and `review` used for generating review data with ffmpeg confersion to jpg sequence.

1.  you need to start OpenPype menu from Resolve/EditTab/Menu/Workspace/Scripts/Comp/**__OpenPype_Menu__**
2.  then select any clips in `main` track and change their color to `Chocolate`
3.  in OpenPype Menu select `Create`
4.  in Creator select `Create Publishable Clip [New]` (temporary name)
5.  set `Rename clips` to True, Master Track to `main` and Use review track to `review` as in picture
    ![image](https://user-images.githubusercontent.com/40640033/102643773-0d419600-4160-11eb-919e-9c2be0aecab8.png)
6.  after you hit `ok` all clips are colored to `ping` and marked with openpype metadata tag
7.  git `Publish` on openpype menu and see that all had been collected correctly. That is the last step for now as rest is Work in progress. Next steps will follow.
