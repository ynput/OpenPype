# Structure of local settings
- local settings do not have any validation schemas right now this should help to see what is stored to local settings and how it works
- they are stored by identifier site_id which should be unified identifier of workstation
- all keys may and may not available on load
- contain main categories: `general`, `applications`, `projects`

## Categories
### General
- ATM contain only label of site
```json
{
    "general": {
        "site_label": "MySite"
    }
}
```

### Applications
- modifications of application executables
- output should match application groups and variants
```json
{
    "applications": {
        "<app group>": {
            "<app name>": {
                "executable": "/my/path/to/nuke_12_2"
            }
        }
    }
}
```

### Projects
- project specific modifications
- default project is stored under constant key defined in `pype.settings.contants`
```json
{
    "projects": {
        "<project name>": {
            "active_site": "<name of active site>",
            "remote_site": "<name of remote site>",
            "roots": {
                "<site name>": {
                    "<root name>": "<root dir path>"
                }
            }
        }
    }
}
```

## Final document
```json
{
    "_id": "<ObjectId(...)>",
    "site_id": "<site id>",
    "general": {
        "site_label": "MySite"
    },
    "applications": {
        "<app group>": {
            "<app name>": {
                "executable": "<path to app executable>"
            }
        }
    },
    "projects": {
        "<project name>": {
            "active_site": "<name of active site>",
            "remote_site": "<name of remote site>",
            "roots": {
                "<site name>": {
                    "<root name>": "<root dir path>"
                }
            }
        }
    }
}
```
