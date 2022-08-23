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

If you are working from home though, you'll need to install it yourself. You should, however, receive the OpenPype installer files from your studio
admin, supervisor or production, because OpenPype versions and executables might not be compatible between studios.  

To install OpenPype you just need to unzip it anywhere on the disk

To use it, you have two options

**openpype_gui.exe** is the most common for artists. It runs OpenPype GUI in system tray. From there you can run all the available tools. To use any of the features, OpenPype must be running in the tray.

**openpype_console.exe** in useful for debugging and error reporting. It opens console window where all the necessary information will appear during user's work. 


<Tabs
  groupId="platforms"
  defaultValue="win"
  values={[
    {label: 'Windows', value: 'win'},
    {label: 'Linux', value: 'linux'},
    {label: 'Mac', value: 'mac'},
  ]}>

<TabItem value="win">

WIP - Windows instructions once installers are finished

</TabItem>
<TabItem value="linux">

WIP - Linux instructions once installers are finished

</TabItem>
<TabItem value="mac">

WIP - Mac instructions once installers are finished

</TabItem>
</Tabs>


## First Launch


When you first start OpenPype, you will be asked to give it some basic information.
### MongoDB

In most cases that will only be your studio MongoDB Address.

It is a URL that you should receive from you studio and most often will look like this `mongodb://username:passwword@mongo.mystudiodomain.com:12345` or  `mongodb://192.168.100.15:27071`, it really depends on your studio setup. When OpenPype Igniter
asks for it, just put it in the corresponding text field and press `install` button.

### OpenPype Version Repository

Sometimes your studio might also ask you to fill in the path to it's version
repository. This is a location where OpenPype will be looking for when checking
if it's up to date and where updates are installed from automatically. 

This pat is usually taken from the database directly, so you shouldn't need it. 


## Updates

If you're connected to your studio, OpenPype will check for, and install updates automatically every time you run it. That's why during the first start, it will go through a quick update installation process, even though you might have just installed it. 


## Advanced use

For more advanced use of OpenPype commands please visit [Admin section](admin_openpype_commands.md).
