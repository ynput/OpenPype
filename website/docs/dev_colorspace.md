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
Adding the `imagio` settings schema is required for any host or module which is processing pixel data.
:::

## Data model
Published representations that are extracted with color managed data store a **colorspaceData** entry in its data: `representation_doc["data"]["colorspaceData"]`.

It's up to the Host implementation to pre-configure the application or workfile to have the correct OCIO config applied.
It's up to the Extractors to set these values for the representation during publishing.
It's up to the Loaders to read these values and apply the correct expected color space.

### Keys
- **colorspace** - string value used in other publish plugins and loaders
- **config** - storing two versions of path.
  - **path** - is formatted and with baked platform root. It is used for possible need to find out where we were sourcing color config during publishing.
  - **template** - unformatted template resolved from settings. It is used for other plugins targeted to remote publish which could be processed at different platform.

### Example
    {
        "colorspace": "linear",
        "config": {
            "path": "/abs/path/to/config.ocio",
            "template": "{project[root]}/path/to/config.ocio"
        }
    }


## How to integrate it into a host
1. The settings for a host should add the `imagio` schema. Ideally near the top of all categories in its `/settings/entities/schemas/system_scheams/host_settings/schema_{host}.json` so it matches the settings layout other hosts.
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

2. Set the OCIO config path for the host to the path returned from `openpype.pipeline.colorspace.get_imageio_config`, for example:
	- set the `OCIO` environment variable before launching the host via a prelaunch hook
	- or (if the host allows) to set the workfile OCIO config path using the host's API

3. Each Extractor exporting pixel data (e.g. image or video) has to inherit from the mixin class `openpype.pipeline.publish.publish_plugins.ColormanagedPyblishPluginMixin` and use `self.set_representation_colorspace` on the representations to be integrated.

The **set_representation_colorspace** method adds `colorspaceData` to the representation. If the `colorspace` passed is not `None` then it is added directly to the representation with resolved config path otherwise a color space is assumed using the configured file rules. If no file rule matches the `colorspaceData` is **not** added to the representation.

An example implementation can be found here: `openpype\hosts\nuke\plugins\publish\extract_render_local.py`


4. The Loader plug-ins should take into account the `colorspaceData` in the published representation's data to allow the DCC to read in the expected color space.
```python
from openpype.pipeline.colorspace import (
    get_imageio_colorspace_from_filepath,
    get_imageio_config,
    get_imageio_file_rules
)

class YourLoader(api.Loader):
  def load(self, context, name=None, namespace=None, options=None):
    path = self.filepath_from_context(context)
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
A custom OCIO config can be set per asset/shot and thus it can happen the current session you are loading into uses a different config than the original context's **colorspaceData** was published with. It's up the loader's implementation to take that into account and decide what to do if the colorspace differs and or might not exist.
:::