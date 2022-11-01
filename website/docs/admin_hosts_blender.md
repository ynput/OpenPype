---
id: admin_hosts_blender
title: Blender
sidebar_label: Blender
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## Blender requirements
Blender integration requires to use **PySide2** module inside blender. Module is different for Blender versions and platforms so can't be bundled with OpenPype.

### How to install

:::info Permissions
This step requires Admin persmission.
:::

<Tabs
  groupId="platforms"
  defaultValue="win"
  values={[
    {label: 'Windows', value: 'win'},
    {label: 'Linux', value: 'linux'},
  ]}>

<TabItem value="win">

Find python executable inside your Blender installation folder. It is usually located in **C:\\Program Files\\Blender Foundation\\Blender {version}\\{version}\\python\\bin\\python.exe** (This may differ in future blender version).

Open Powershell or Command Prompt as Administrator and run commands below.

*Replace `C:\Program Files\Blender Foundation\Blender 2.83\2.83\python\bin` with your path.*

```bash
# Change directory to python executable directory.
> cd C:\Program Files\Blender Foundation\Blender 2.83\2.83\python\bin

# Run pip install command.
> python -m pip install PySide2
```

</TabItem>

<TabItem value="linux">

Procedure may differ based on Linux distribution and blender distribution. Some Blender distributions are using system Python in that case it is required to install PySide2 using pip to system python (Not tested).

**These instructions are for Blender using bundled python.**

Find python executable inside your blender application.

:::note Find python executable in Blender
You can launch Blender and in "Scripting" section enter commands to console.
```bash
>>> import bpy
>>> print(bpy.app.binary_path_python)
'/path/to/python/executable'
```
:::

Open terminal and run pip install command below.

*Replace `/usr/bin/blender/2.83/python/bin/python3.7m` with your path.*
```bash
> /usr/bin/blender/2.83/python/bin/python3.7m -m pip install PySide2
```

:::warning No module named pip
If you get error `No module named pip` you'll have to do few steps first. Open new terminal and run the python executable from Blender (entering full path).
```bash
# Run Python executable
> /usr/bin/blender/2.83/python/bin/python3.7m
# Python process should start
>>> import ensurepip
>>> ensurepip.bootstrap()
```
You can close new terminal. Run pip install command above again. Now should work as expected.
:::

</TabItem>

</Tabs>

## Settings
### General
- Use file compress on save: All published files are compressed using Blender's native algorithm.
- Paths background management: In order to make remote working easier using sites sync by keeping blend file's references during file copies, paths must be constantly converted between relative and absolute. The user must always work in absolute paths, and the published files must store paths as relative. This option ensures this conversion in background. In short:
  - Published files: Relative paths
  - Workfiles: Absolute paths