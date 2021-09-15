---
id: module_site_sync
title: Site Sync Administration
sidebar_label: Site Sync
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';


:::warning
**This feature is** currently **in a beta stage** and it is not recommended to rely on it fully for production.
:::

Site Sync allows users and studios to synchronize published assets between multiple 'sites'. Site denotes a storage location,
which could be a physical disk, server, cloud storage. To be able to use site sync, it first needs to be configured. 

The general idea is that each user acts as an individual site and can download and upload any published project files when they are needed. that way, artist can have access to the whole project, but only every store files that are relevant to them on their home workstation. 

:::note
At the moment site sync is only able to deal with publishes files. No workfiles will be synchronized unless they are published. We are working on making workfile synchronization possible as well. 
:::

## System Settings

To use synchronization, *Site Sync* needs to be enabled globally in **OpenPype Settings/System/Modules/Site Sync**.

![Configure module](assets/site_sync_system.png)


## Project Settings

Sites need to be made available for each project. Of course this is possible to do on the default project as well, in which case all other projects will inherit these settings until overriden explicitly.

You'll find the setting in **Settings/Project/Global/Site Sync**

The attributes that can be configured will vary between sites and their providers. 

## Local settings

Each user should configure root folder for their 'local' site via **Local Settings** in OpenPype Tray. This folder will be used for all files that the user publishes or downloads while working on a project. Artist has the option to set the folder as "default"in which case it is used for all the projects, or it can be set on a project level individually.

Artists can also override which site they use as active and remote if need be. 

![Local overrides](assets/site_sync_local_setting.png)


## Sites 

By default there are two sites created for each OpenPype installation:
- **studio** - default site - usually a centralized mounted disk accessible to all artists. Studio site is used if Site Sync is disabled.
- **local** - each workstation or server running OpenPype Tray receives its own with unique site name. Workstation refers to itself as "local"however all other sites will see it under it's unique ID.

Artists can explore their site ID by opening OpenPype Info tool by clicking on a version number in the tray app. 

Many different sites can be created and configured on the system level, and some or all can be assigned to each project.

Each OpenPype Tray app works with two sites at one time. (Sites can be the same, and no synching is done in this setup).

Sites could be configured differently per project basis. 


## Providers

Each site implements a so called `provider` which handles most common operations (list files, copy files etc.) and provides interface with a particular type of storage. (disk, gdrive, aws, etc.)
Multiple configured sites could share the same provider with different settings (multiple mounted disks - each disk can be a separate site, while
all share the same provider).

**Currently implemented providers:**

### Local Drive

Handles files stored on disk storage.

Local drive provider is the most basic one that is used for accessing all standard hard disk storage scenarios. It will work with any storage that can be mounted on your system in a standard way. This could correspond to a physical external hard drive, network mounted storage, internal drive or even VPN connected network drive. It doesn't care about how te drive is mounted, but you must be able to point to it with a simple directory path.

Default sites `local` and `studio` both use local drive provider.


### Google Drive

Handles files on Google Drive (this). GDrive is provided as a production example for implementing other cloud providers

Let's imagine a small globally distributed studio which wants all published work for all their freelancers uploaded to Google Drive folder.

For this use case admin needs to configure:
- how many times it tries to synchronize file in case of some issue (network, permissions)
- how often should synchronization check for new assets
- sites for synchronization - 'local' and 'gdrive' (this can be overriden in local settings)
- user credentials
- root folder location on Google Drive side

Configuration would look like this:

![Configure project](assets/site_sync_project_settings.png)

*Site Sync* for Google Drive works using its API: https://developers.google.com/drive/api/v3/about-sdk

To configure Google Drive side you would need to have access to Google Cloud Platform project: https://console.cloud.google.com/ 

To get working connection to Google Drive there are some necessary steps:
- first you need to enable GDrive API: https://developers.google.com/drive/api/v3/enable-drive-api
- next you need to create user, choose **Service Account** (for basic configuration no roles for account are necessary) 
- add new key for created account and download .json file with credentials
- share destination folder on the Google Drive with created account (directly in GDrive web application)
- add new site back in OpenPype Settings, name as you want, provider needs to be 'gdrive'
- distribute credentials file via shared mounted disk location

### Custom providers

If a studio needs to use other services for cloud storage, or want to implement totally different storage providers, they can do so by writing their own provider plugin. We're working on a developer documentation, however, for now we recommend looking at `abstract_provider.py`and `gdrive.py` inside `openpype/modules/sync_server/providers` and using it as a template.

