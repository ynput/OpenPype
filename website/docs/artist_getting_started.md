---
title: Getting started with OpenPype
sidebar_label: Getting started
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';



## Working in the studio

In studio environment you should have OpenPype already installed and deployed,  so you can start using it without much setup. Your admin has probably put OpenPype icon on your desktop or even had your computer set up so OpenPype will start automatically.

If this is not the case, please contact your administrator to consult on how to launch OpenPype in your studio

## Working from home

If you are working from **home** though, you'll **need to install** it yourself. You should, however, receive the OpenPype installer files from your studio
admin, supervisor or production, because OpenPype versions and executables might not be compatible between studios.

Installing OpenPype is possible by Installer or by unzipping downloaded ZIP archive to any drive location.

:::tip Using the OpenPype Installer
See the [Installation section](artist_install.md) for more information on how to use the OpenPype Installer
:::


You can run OpenPype by desktop "OP" icon (if it exists after installing) or by directly executing

**openpype_gui.exe** located in the OpenPype folder. This executable being suitable **for artists**.

or alternatively by

**openpype_console.exe** which is more suitable for **TDs/Admin** for debugging and error reporting. This one runs with
opened console window where all the necessary info will appear during user's work session.

:::tip Is OpenPype running?
OpenPype runs in the operating system's tray. If you see turquoise OpenPype icon in the tray you can easily tell OpenPype is currently running.
Keep in mind that on Windows this icon might be hidden by default, in which case, the artist can simply drag the icon down to the tray.
:::

![Systray](assets/artist_systray.png)


## First Launch


When you first start OpenPype, you will be asked to fill in some basic information.

### MongoDB

In most cases you will only have to supply the MongoDB Address.
It's the database URL you should have received from your Studio admin and often will look like this

`mongodb://username:passwword@mongo.mystudiodomain.com:12345`

 or

 `mongodb://192.168.100.15:27071`

it really depends on your studio setup. When OpenPype Igniter
asks for it, just put it in the corresponding text field and press `install` button.

### OpenPype Version Repository

Sometimes your Studio might also ask you to fill in the path to its version
repository. This is a location where OpenPype will search for the latest versions, check
if it's up to date and where updates are installed from automatically.

This path is usually taken from the database directly, so you shouldn't need it.


## Updates

If you're connected to your Studio, OpenPype will check for, and install updates automatically every time you run it. That's why during the first start it can go through a quick update installation process, even though you might have just installed it.


## Advanced Usage

For more advanced use of OpenPype commands please visit [Admin section](admin_openpype_commands.md).
