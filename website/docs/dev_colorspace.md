---
id: dev_colorspace
title: Colorspace Management and Distribution
sidebar_label: Colorspace
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## Introduction
Defines the distribution of colors and OCIO config during publishing. Once colorspace data are captured and integrated into representation loaders could use them for loading image and video data with correct colorspace.

:::warning Color Management (ImageIO)
Settings schema is requred for any host or module which is processing pixel data.
:::

## Data model
The *colorspaceData* are stored at root of representation dictionary during publishing. Once they are integrated into representation db document they are stored as *representation_doc.data["colorspaceData"]*

### Keys
- **colorspace** - string value used in other publish plugins and loaders
- **configData** - storing two versions of path.
  - **path** - is formated and with baked platform root. It is used for posible need to find out where we were sourcing color config during publishing.
  - **template** - unformated tempate resolved from settings. It is used for other plugins targeted to remote publish which could be processed at different platform.

### Example
    {
        "colorspace": "linear",
        "configData": {
            "path": "/abs/path/to/config.ocio",
            "template": "{project[root]}/path/to/config.ocio"
        }
    }


## How to integrate it into a host
1. Each host setting schema should have following shemas. Ideally at top of all categories so it mimic already defined order at other hosts.
```json
{
    "key": "imageio",
    "type": "dict",
    "label": "Color Management (ImageIO)",
    "is_group": true,
    "children": [
        {
            "type": "schema",
            "name": "schema_imageio_config"
        },
        {
            "type": "schema",
            "name": "schema_imageio_file_rules"
        }

    ]
}
```

2. Use any mechanism to set OCIO config to host app resolved from `openpype\pipeline\colorspace.py:get_imageio_config`
	-	either set OCIO environment during host launching via pre-launch hook
	- or to set workfile ocio config path if host api is available

3. Each pixle related exporter plugins has to use parent class `openpype\pipeline\publish\publish_plugins.py:ExtractorColormanaged` and use it similarly as it is already implemented here `openpype\hosts\nuke\plugins\publish\extract_render_local.py`
- **get_colorspace_settings**: is solving all settings for the host context
- **set_representation_colorspace**: is adding colorspaceData to representation. If the colorspace is known then it is added directly to the representation with resolved config path.

4. Implement the loading procedure. Each loader which needs to have colorspace (detected from representation doc) set to DCC reader nodes should implement following code.
```python
from openpype.pipeline.colorspace import (
    get_imageio_colorspace_from_filepath,
    get_imageio_config,
    get_imageio_file_rules
)

class YourLoader(api.Loader):
  def load(self, context, name=None, namespace=None, options=None):
    path = self.fname
    colorspace_data = context["representation"]["data"].get("colorspaceData", {})
    colorspace = (
      colorspace_data.get("colorspace")
      # try to match colorspace from file rules
      or self.get_colorspace_from_file_rules(path, context)
    )

    # pseudocode
    load_file(path, colorspace=colorspace)

  def get_colorspace_from_file_rules(self, path, context)
    project_name = context.data["projectName"]
    host_name = context.data["hostName"]
    anatomy_data = context.data["anatomyData"]
    project_settings_ = context.data["project_settings"]

    config_data = get_imageio_config(
        project_name, host_name,
        project_settings=project_settings_,
        anatomy_data=anatomy_data
    )
    file_rules = get_imageio_file_rules(
        project_name, host_name,
        project_settings=project_settings_
    )
    # get matching colorspace from rules
    colorspace = get_imageio_colorspace_from_filepath(
      path, host_name, project_name,
      config_data=config_data,
      file_rules=file_rules,
      project_settings=project_settings
    )
```

:::warning Loading
Current loader's host will be using a different OCIO.config file than the original context **colorspaceData** have been published with. There is no way at the moment a DCC can use multiple ocio configs at one workfile.
:::