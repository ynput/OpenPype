---
id: dev_host_implementation
title: Host implementation
sidebar_label: Host implementation
toc_max_heading_level: 4
---

Host is an integration of DCC but in most of cases have logic that need to be handled before DCC is launched. Then based on abilities (or purpose) of DCC the integration can support different pipeline workflows.

## Pipeline workflows
Workflows available in OpenPype are Workfiles, Load and Create-Publish. Each of them may require some functionality available in integration (e.g. call host API to achieve certain functionality). We'll go through them later.

## How to implement and manage host
At this moment there is not fully unified way how host should be implemented but we're working on it. Host should have a "public face" code that can be used outside of DCC and in-DCC integration code. The main reason is that in-DCC code can have specific dependencies for python modules not available out of it's process. Hosts are located in `openpype/hosts/{host name}` folder. Current code (at many places) expect that the host name has equivalent folder there. So each subfolder should be named with the name of host it represents.

### Recommended folder structure
```python
openpype/hosts/{host name}
│
│  # Content of DCC integration - with in-DCC imports
├─ api
│   ├─ __init__.py
│   └─ [DCC integration files]
│
│  # Plugins related to host - dynamically imported (can contain in-DCC imports)
├─ plugins
│   ├─ create
│   │   └─ [create plugin files]
│   ├─ load
│   │   └─ [load plugin files]
│   └─ publish
│       └─ [publish plugin files]
│
│  # Launch hooks - used to modify how application is launched
├─ hooks
│   └─ [some pre/post launch hooks]
|
│  # Code initializing host integration in-DCC (DCC specific - example from Maya)
├─ startup
│   └─ userSetup.py
│
│  # Public interface
├─ __init__.py
└─ [other public code]
```

### Launch Hooks
Launch hooks are not directly connected to host implementation, but they can be used to modify launch of process which may be crucial for the implementation. Launch hook are plugins called when DCC is launched. They are processed in sequence before and after launch. Pre launch hooks can change how process of DCC is launched, e.g. change subprocess flags, modify environments or modify launch arguments. If prelaunch hook crashes the application is not launched at all. Postlaunch hooks are triggered after launch of subprocess. They can be used to change statuses in your project tracker, start timer, etc. Crashed postlaunch hooks have no effect on rest of postlaunch hooks or launched process. They can be filtered by platform, host and application and order is defined by integer value. Hooks inside host are automatically loaded (one reason why folder name should match host name) or can be defined from modules. Hooks execution share same launch context where can be stored data used across multiple hooks (please be very specific in stored keys e.g. 'project' vs. 'project_name'). For more detailed information look into `openpype/lib/applications.py`.

### Public interface
Public face is at this moment related to launching of the DCC. At this moment there there is only option to modify environment variables before launch by implementing function `add_implementation_envs` (must be available in `openpype/hosts/{host name}/__init__.py`). The function is called after pre launch hooks, as last step before subprocess launch, to be able set environment variables crucial for proper integration. It is also good place for functions that are used in prelaunch hooks and in-DCC integration. Future plans are to be able get workfiles extensions from here. Right now workfiles extensions are hardcoded in `openpype/pipeline/constants.py` under `HOST_WORKFILE_EXTENSIONS`, we would like to handle hosts as addons similar to OpenPype modules, and more improvements which are now hardcoded.

### Integration
We've prepared base class `HostBase` in `openpype/host/host.py` to define minimum requirements and provide some default method implementations. The minimum requirement for a host is `name` attribute, this host would not be able to do much but is valid. To extend functionality we've prepared interfaces that helps to identify what is host capable of and if is possible to use certain tools with it. For those cases we defined interfaces for each workflow. `IWorkfileHost` interface add requirement to implement workfiles related methods which makes host usable in combination with Workfiles tool. `ILoadHost` interface add requirements to be able load, update, switch or remove referenced representations which should add support to use Loader and Scene Inventory tools. `INewPublisher` interface is required to be able use host with new OpenPype publish workflow. This is what must or can be implemented to allow certain functionality. `HostBase` will have more responsibility which will be taken from global variables in future. This process won't happen at once, but will be slow to keep backwards compatibility for some time.

#### Example
```python
from openpype.host import HostBase, IWorkfileHost, ILoadHost


class MayaHost(HostBase, IWorkfileHost, ILoadHost):
    def open_workfile(self, filepath):
        ...

    def save_current_workfile(self, filepath=None):
        ...

    def get_current_workfile(self):
        ...
    ...
```

### Install integration
We have prepared a host class, now where and how to initialize it's object? This part is DCC specific. In DCCs like Maya with embedded python and Qt we use advantage of being able to initialize object of the class directly in DCC process on start, the same happens in Nuke, Hiero and Houdini. In DCCs like Photoshop or Harmony there is launched OpenPype (python) process next to it which handles host initialization and communication with the DCC process (e.g. using sockects). Created object of host must be installed and registered to global scope of OpenPype. Which means that at this moment one process can handle only one host at a time.

#### Install example (Maya startup file)
```python
from openpype.pipeline import install_host
from openpype.hosts.maya.api import MayaHost


host = MayaHost()
install_host(host)
```

Function `install_host` cares about installing global plugins, callbacks and register host. Host registration means that the object is kept in memory and is accessible using `get_registered_host()`.

### Using UI tools
Most of functionality in DCCs is provided to artists by using UI tools. We're trying to keep UIs consistent so we use same set of tools in each host, all or most of them are Qt based. There is a `HostToolsHelper` in `openpype/tools/utils/host_tools.py` which unify showing of default tools, they can be showed almost at any point. Some of them are validating if host is capable of using them (Workfiles, Loader and Scene Inventory) which is related to [pipeline workflows](#pipeline-workflows). `HostToolsHelper` provides API to show tools but host integration must care about giving artists ability to show them. Most of DCCs have some extendable menu bar where is possible to add custom actions, which is preferred approach how to give ability to show the tools.
