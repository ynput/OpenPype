---
id: admin_hosts_houdini
title: Houdini
sidebar_label: Houdini
---
## General Settings
### JOB Path
Specify a studio-wide `JOB` path.<br>
The Houdini `$JOB` path can be customized through project settings with a (dynamic) path that will be updated on context changes, e.g. when switching to another asset or task.

Disabling this feature will leave `$JOB` var unmanaged and thus no context update changes will occur.

JOB Path can be:
- Arbitrary path
- Openpype template path
    > This allows dynamic values for assets or shots.<br>
    > Using template keys is supported but formatting keys capitalization variants is not,
    >   e.g. {Asset} and {ASSET} won't work
- Empty
    > In this case, JOB will be synced to HIP

![update job on context change](assets/houdini/update-job-context-change.png)



## Shelves Manager
You can add your custom shelf set into Houdini by setting your shelf sets, shelves and tools in **Houdini -> Shelves Manager**.
![Custom menu definition](assets/houdini-admin_shelvesmanager.png)

The Shelf Set Path is used to load a .shelf file to generate your shelf set. If the path is specified, you don't have to set the shelves and tools.
