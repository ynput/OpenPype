Synchronization server
---------------------
This server is scheduled at start of Pype, it periodically checks avalon DB
for 'representation' records which have in theirs files.sites record with 
name: 'gdrive' (or any other site name from 'gdrive.json') without 
field 'created_dt'.

This denotes that this representation should be synced to GDrive.
Records like these are created by IntegrateNew process based on configuration.
Leave 'config.json.remote_site' empty for not synchronizing at all.

One provider could have multiple sites. (GDrive implementation is 'a provider',
target folder on it is 'a site')

Quick HOWTOs:
-------------
I want to start syncing my newly published files:
------------------------------------------------

- Check that Sync server is enabled globally in 
    `pype/settings/defaults/system_settings/modules.json`
    
- Get credentials for service account, share target folder on Gdrive with it

- Set path to stored credentials file in 
    `pype/settings/defaults/project_settings/global.json`.`credentials_url`
    
- Set name of site, root folder and provider('gdrive' in case of Google Drive) in 
    `pype/settings/defaults/project_settings/global.json`.`sites`
    
- Update `pype/settings/defaults/project_settings/global.json`.`remote_site`
to name of site you set in previous step.

- Check that project setting is enabled (in this `global.json` file)

- Start Pype and publish

My published file is not syncing:
--------------------------------

- Check that representation record contains for all 'files.sites' skeleton in 
format: `{name: "MY_CONFIGURED_REMOTE_SITE"}`
- Check if that record doesn't have already 'created_dt' filled. That would 
denote that file was synced but someone might have had removed it on remote
site.
- If that records contains field "error", check that "tries" field doesn't 
contain same value as threshold in config.json.retry_cnt. If it does fix 
the problem mentioned in 'error' field, delete 'tries' field.

I want to sync my already published files:
-----------------------------------------

- Configure your Pype for syncing (see first section of Howtos).
- Manually add skeleton {name: "MY_CONFIGURED_REMOTE_SITE"} to all 
representation.files.sites:
`db.getCollection('MY_PROJECT').update({type:"representation"}, 
{$set:{"files.$[].sites.MY_CONFIGURED_REMOTE_SITE" : {}}}, true, true)`

I want to create new custom provider:
-----------------------------------
- take `providers\abstract_provider.py` as a base class
- create provider class in `providers` with a name according to a provider (eg. 'gdrive.py' for gdrive provider etc.)
- upload provider icon in png format, 24x24, into `providers\resources`, its name must follow name of provider (eg. 'gdrive.png' for gdrive provider)
- register new provider into `providers.lib.py`, test how many files could be manipulated at same time, check provider's API for limits

Needed configuration:
--------------------
`pype/settings/defaults/project_settings/global.json`.`sync_server`:
 - `"local_id": "local_0",` -- identifier of user pype
 - `"retry_cnt": 3,`        -- how many times try to synch file in case of error
 - `"loop_delay": 60,`      -- how many seconds between sync loops
 - `"publish_site": "studio",` -- which site user current, 'studio' by default, 
                              could by same as 'local_id' if user is working
                              from home without connection to studio 
                              infrastructure
 - `"remote_site": "gdrive"` -- key for site to synchronize to. Must match to site
                             configured lower in this file.
                             Used in IntegrateNew to prepare skeleton for 
                             syncing in the representation record.
                             Leave empty if no syncing is wanted.
  This is a general configuration, 'local_id', 'publish_site' and 'remote_site'
  will be set and changed by some GUI in the future.                           
  
`pype/settings/defaults/project_settings/global.json`.`sync_server`.`sites`:
 ```- "gdrive": {  - site name, must be unique
 -     "provider": "gdrive" -- type of provider, must be registered in 'sync_server\providers\lib.py'
 -     "credentials_url": "/my_secret_folder/credentials.json", 
            -- path to credentials for service account
 -     "root": {     -- "root": "/My Drive" in simple scenario, config here for
                    --  multiroot projects
 -           "root_one": "/My Drive/work_folder",
 -           "root_tow": "/My Drive/publish_folder"
     }
  }``
  
  

