module.exports = {
    "artist": [
      {
        type: "category",
        collapsed: false,
        label: "Workflow",
        items: [
            "artist_getting_started",
            "artist_concepts",
            "artist_publish",
            "artist_tools"
        ]
      },
      {
        type: "category",
        collapsed: false,
        label: "Integrations",
        items: [
            "artist_hosts_nukestudio",
            "artist_hosts_nuke",
            "artist_hosts_maya",
            "artist_hosts_harmony",
            "artist_hosts_photoshop",
            "artist_hosts_unreal",
            {
              type: "category",
              label: "Ftrack",
              items: [
                "artist_ftrack",
                "manager_ftrack",
                "manager_ftrack_actions"
              ]
            }
        ]
      },
    ],
    "Admin": {
          "Deployment": ["admin_getting_started",
                    "admin_install",
                    "admin_config",
                    "admin_ftrack",
                    "admin_hosts",
                    "admin_pype_commands",
                    "admin_setup_troubleshooting"],
          'Configuration':["admin_presets_nukestudio",
                    "admin_presets_ftrack",
                    "admin_presets_maya",
                    "admin_presets_plugins",
                    "admin_presets_tools"],
          "Release Notes":[
              "changelog",
              "update_notes"
          ]
    },
}
