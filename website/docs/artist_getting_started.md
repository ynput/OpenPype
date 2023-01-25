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

Installing OpenPype is possible by Windows installer or by unzipping it anywhere on the disk from downloaded ZIP archive.

For more detailed info about installation on different OS please visit [Installation section](artist_install.md).

There are two ways running OpenPype

first most common one by using OP icon on the Desktop triggering

**openpype_gui.exe** suitable **for artists**. It runs OpenPype GUI in the OS tray. From there you can run all the available tools. To use any of the features, OpenPype must be running in the tray.

or alternatively by using

**openpype_console.exe** located in the OpenPype folder which is suitable for **TDs/Admin** for debugging and error reporting. This one runs with opened console window where all the necessary info will appear during user's work session. 


## First Launch


When you first start OpenPype, you will be asked to fill in some basic informations.

### MongoDB

In most cases that will only be your studio MongoDB Address.
It's a URL that you should have received from your Studio admin and most often will look like this 

`mongodb://username:passwword@mongo.mystudiodomain.com:12345`

 or

 `mongodb://192.168.100.15:27071`

it really depends on your studio setup. When OpenPype Igniter
asks for it, just put it in the corresponding text field and press `install` button.

### OpenPype Version Repository

Sometimes your Studio might also ask you to fill in the path to it's version
repository. This is a location where OpenPype will be looking for when checking
if it's up to date and where updates are installed from automatically. 

This path is usually taken from the database directly, so you shouldn't need it. 


## Updates

If you're connected to your Studio, OpenPype will check for, and install updates automatically every time you run it. That's why during the first start, it will go through a quick update installation process, even though you might have just installed it. 


## Advanced Usage

For more advanced use of OpenPype commands please visit [Admin section](admin_openpype_commands.md).
