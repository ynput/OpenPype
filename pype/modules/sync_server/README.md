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

Get credentials for service account, share target folder on Gdrive with it
Set path to stored credentils file in gdrive.json
Set name of site, root folder in gdrive.json
Update config.json/remote_site to name of site you set in previous step
Start Pype and publish

My published file is not syncing:
--------------------------------

Check that representation record contains for all 'files.site' skeleton in 
format: {name: "MY_CONFIGURED_REMOTE_SITE"}
Check if that record doesn't have already 'created_dt' filled. That would 
denote that file was synced but someone might have had removed it on remote
site.
If that records contains field "error", check that "tries" field doesn't 
contain same value as threshold in config.json.retry_cnt. If it does fix 
the problem mentioned in 'error' field, delete 'tries' field.

I want to sync my already published files:
-----------------------------------------

Configure your Pype for syncing (see first section of Howtos).
Manually add skeleton {name: "MY_CONFIGURED_REMOTE_SITE"} to all 
representation.files.sites:
db.getCollection('MY_PROJECT').update({type:"representation"}, 
{$set:{"files.$[].sites.MY_CONFIGURED_REMOTE_SITE" : {}}}, true, true)

Needed configuration:
--------------------
pype-config/presets/config.json:
  "local_id": "local_0", -- identifier of user pype
  "retry_cnt": 3,        -- how many times try to synch file in case of error
  "loop_delay": 60,      -- how many seconds between sync loops
  "active_site": "studio", -- which site user current, 'studio' by default, 
                              could by same as 'local_id' if user is working
                              from home without connection to studio 
                              infrastructure
  "remote_site": "gdrive" -- key for site to synchronize to. Must match to site
                             configured in 'gdrive.json'.
                             Used in IntegrateNew to prepare skeleton for 
                             syncing in the representation record.
                             Leave empty if no syncing is wanted.
  This is a general configuration, 'local_id', 'active_site' and 'remote_site'
  will be set and changed by some GUI in the future.                           
  
pype-config/presets/gdrive.json:
  "gdrive": {  - site name, must be unique
      "credentials_url": "/my_secret_folder/credentials.json", 
            -- path to credentials for service account
      "root": {     -- "root": "/My Drive" in simple scenario, config here for
                    --  multiroot projects
            "root_one": "/My Drive/work_folder",
            "root_tow": "/My Drive/publish_folder"
      }
  }
  
  

