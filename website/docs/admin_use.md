---
id: admin_use
title: Install and Run 
sidebar_label: Install & Run
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';


## Install

You can install OpenPype on individual workstations the same way as any other software. 
When you create you build, you will end up with an installation package for the platform 
that was used for the build.

- Windows: `OpenPype-3.0.0.msi`
- Linux: `OpenPype-3.0.0.zip`
- Mac: `OpenPype-3.0.0.dmg`

After OpenPype is installed, it will ask the user for further installation if it detects a
newer version in the studio update location.

## Run OpenPype

To use OpenPype on a workstation simply run the executable that was installed.
On the first run the user will be prompted to for OpenPype Mongo URL. 
This piece of information needs to be provided to the artist by the admin setting 
up OpenPype in the studio.

Once artist enters the Mongo URL address, OpenPype will remember the connection for the 
next launch, so it is a one time process.From that moment OpenPype will do it's best to 
always keep up to date with the latest studio updates. 

If the launch was successfull, the artist should see a green OpenPype logo in their
tray menu. Keep in mind that on Windows this icon might be hidden by default, in which case,
the artist can simply drag the icon down to the tray.