---
id: admin_distribute
title: Distribute
sidebar_label: Distribute
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

To let your artists to use OpenPype, you'll need to distribute the frozen executables to them.

Distribution consists of two parts

 ### 1. OpenPype Igniter
 
 This is the base application that will be installed locally on each workstation.
 It is self contained (frozen) software that also includes all of the OpenPype codebase with the version
 from the time of the build.

 Igniter package is around 500MB and preparing an updated version requires you to re-build pype. That would be 
 inconvenient for regular and quick distribution of production updates and fixes. So you can distribute those
 independently, without requiring you artists to re-install every time.

 ### 2. OpenPype Codebase

When you upgrade your studio pype deployment to a new version or make any local code changes, you can distribute
these changes to your artists, without the need of re-building OpenPype, by using `create_zip` tool provided.
The resulting zip needs to be made available to the artists and it will override their local OpenPype install
with the updated version.

You have two ways of making this happen

#### Automatic Updates

Every time and Artist launches OpenPype on their workstation, it will look to a pre-defined 
[openPype update location](admin_settings_system.md#openpype-deployment-control) for any versions that are newer than the
latest, locally installed version. If such version is found, it will be downloaded,  
automatically extracted to the correct place and launched. This will become the default 
version to run for the artist, until a higher version is detected in the update location again.

#### Manual Updates

If for some reason you don't want to use the automatic updates, you can distribute your
zips manually. Your artist will then have to put them to the correct place on their disk.
Zips will be automatically unzipped there.

The default locations are:

- Windows: `%LOCALAPPDATA%\pypeclub\openpype`
- Linux: `~/.local/share/pypeclub/openpype`
- Mac: `~/Library/Application Support/pypeclub/openpype`


### Staging vs. Production
You can have version of OpenPype with experimental features you want to try somewhere but you
don't want to disrupt your production. You can tag version as **staging** simply by appending `+staging`
to its name.

So if you have OpenPype version like `OpenPype-v3.0.0.zip` just name it `OpenPype-v3.0.0+staging.zip`.
When both these versions are present, production one will always take precedence over staging.

You can run OpenPype with `--use-staging` argument to add use staging versions.

:::note
Running staging version is identified by orange **P** icon in system tray.
:::

### OpenPype versioning

OpenPype version control is based on semantic versioning.

:::note
The version of OpenPype is indicated by the variable `__version__` in the file `.\openpype\version.py`.
:::

For example OpenPype will consider the versions in this order: `3.8.0-nightly` < `3.8.0-nightly.1` < `3.8.0-rc.1` < `3.8.0` < `3.8.1-nightly.1` <`3.8.1` < `3.9.0` < `3.10.0` < `4.0.0`.

See https://semver.org/ for more details.

For studios customizing the source code of OpenPype, a practical approach could be to build by adding a name and a number after the PATCH and not to deploy 3.8.0 from original OpenPype repository. For example, your builds will be: `3.8.0-yourstudio.1` < `3.8.0-yourstudio.2` < `3.8.1-yourstudio.1`.