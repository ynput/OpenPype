---
id: module_royalrender
title: Royal Render Administration
sidebar_label: Royal Render
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';


## Preparation

For [Royal Render](hhttps://www.royalrender.de/) support you need to set a few things up in both OpenPype and Royal Render itself

1. Deploy OpenPype executable to all nodes of Royal Render farm. See [Install & Run](admin_use.md)

2. Enable Royal Render Module in the [OpenPype Admin Settings](admin_settings_system.md#royal-render).

3. Point OpenPype to your Royal Render installation in the [OpenPype Admin Settings](admin_settings_system.md#royal-render).

4. Install our custom plugin and scripts to your RR repository. It should be as simple as copying content of `openpype/modules/royalrender/rr_root` to `path/to/your/royalrender/repository`.


## Configuration

OpenPype integration for Royal Render consists of pointing RR to location of Openpype executable. That is being done by copying `_install_paths/OpenPype.cfg` to
RR root folder. This file contains reasonable defaults. They could be changed in this file or modified Render apps in `rrControl`.


## Debugging

Current implementation uses dynamically build '.xml' file which is stored in temporary folder accessible by RR. It might make sense to
use this Openpype built file and try to run it via `*__rrServerConsole` executable from command line in case of unforeseeable issues.

## Known issues

Currently environment values set in Openpype are not propagated into render jobs on RR. It is studio responsibility to synchronize environment variables from Openpype with all render nodes for now.
