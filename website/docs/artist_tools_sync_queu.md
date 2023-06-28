---
id: artist_tools_sync_queue
title: Sync Queue
sidebar_label: Sync Queue
description: Track sites synchronization progress.
---

# Sync Queue

## Details

If **Site Sync** is configured for a project, each asset is marked to be synchronized to a remote site during publishing.
Each artist's OpenPype Tray application handles synchronization in background, it looks for all representation which 
are marked with the site of the user (unique site name per artist) and remote site.

Artists then can see progress of synchronization via **Sync Queue** link in the Tray application.

Artists can see all synced representation in this dialog with helpful information such as when representation was created, when it was synched,
status of synchronization (OK or Fail) etc.

## Usage

With this app artists can modify synchronized representation, for example mark failed representation for re-sync etc.

![Sync Queue](assets/site_sync_sync_queue.png)

Actions accessible by context menu on single (or multiple representations):
- *Open in Explorer* - if site is locally accessible, open folder with it with OS based explorer
- *Re-sync Active Site* - mark artist own side for re-download (repre must be accessible on remote side)
- *Re-sync Remote Site* - mark representation for re-upload
- *Completely remove from local* - removes tag of synchronization to artist's local site, removes files from disk (available only for personal sites)
- *Change priority* - mark representations with higher priority for faster synchronization run

Double click on any of the representation open Detail dialog with information about all files for particular representation.
In this dialog error details could be accessed in the context menu.

#### Context menu on project name
Artists can also Pause whole server or specific project for synchronization. In that state no download/upload is being run.
This might be helpful if the artist is not interested in a particular project for a while or wants to save bandwidth data limit for a bit.

Another option is `Validate files on active site`. This option triggers process where all representation of the selected project are looped through, file paths are resolved for active site and
if paths point to local system, paths are physically checked if files are existing. If file exists and representation is not marked to be present on 'active_site' in DB, DB is updated 
to follow that. 

This might be useful if artist has representation files that Site Sync doesn't know about (newly attached external drive with representations from studio).
This project might take a while!
