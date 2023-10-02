---
id: admin_settings_local
title: Working with local settings
sidebar_label: Working with local settings
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

OpenPype stores some of it's settings and configuration in local file system. These settings are specific to each individual machine and provides the mechanism for local overrides

**Local Settings** GUI can be started from the tray menu.

![Local Settings](assets/settings/settings_local.png)

## Categories

### OpenPype Mongo URL
The **Mongo URL** is the database URL given by your Studio. More details [here](artist_getting_started.md#mongodb).

### General
**OpenPype Username** : enter your username (if not provided, it uses computer session username by default). This username is used to sign your actions on **OpenPype**, for example the "author" on a publish.

**Admin permissions** : When enabled you do not need to enter a password (if defined in Studio Settings) to access to the **Admin** section.
### Experimental tools
Future version of existing tools or new ones.
### Environments
Local replacement of the environment data of each software and additional internal data necessary to be loaded correctly.

### Applications
Local override of software executable paths for each version. More details [here](admin_settings_system.md#applications).

### Project Settings
The **Project Settings** allows to determine the root folder. More details [here](module_site_sync.md#local-settings).
