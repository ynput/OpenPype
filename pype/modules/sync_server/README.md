Synchronization server
---------------------
This server is scheduled at start of Pype, it periodically checks avalon DB
for 'representation' records which have in theirs files.sites record with 
name: 'gdrive' without field 'created_dt'.
This denotes that this representation should be sync to GDrive.
Records like these are created by IntegrateNew process based on configuration.

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
  "remote_site": "gdrive" -- key for site to synchronize to (currently only
                            'gdrive' implemented, but could be any provider
                             implemented in 'pype/modules/sync_server')
pype-config/presets/gdrive.json:
  "credentials_url": "/my_secret_folder/credentials.json", 
        -- path to credentials for service account
  "root": {     -- "root": "/My Drive" in simple scenario, this could be for
                    multiroot projects
        "root_one": "/My Drive/work_folder",
        "root_tow": "/My Drive/publish_folder"
  }
  
  

