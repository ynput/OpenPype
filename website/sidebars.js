module.exports = {
    artist: [
        {
            type: "category",
            collapsed: false,
            label: "General",
            items: [
                "artist_getting_started",
                "artist_concepts",
                "artist_publish",
                "artist_tools",
                "artist_install"
            ],
        },
        {
            type: "category",
            collapsed: false,
            label: "Integrations",
            items: [
                "artist_hosts_hiero",
                "artist_hosts_nuke_tut",
                "artist_hosts_maya",
                "artist_hosts_blender",
                "artist_hosts_harmony",
                "artist_hosts_houdini",
                "artist_hosts_aftereffects",
                "artist_hosts_resolve",
                "artist_hosts_photoshop",
                "artist_hosts_tvpaint",
                "artist_hosts_unreal",
                {
                    type: "category",
                    label: "Ftrack",
                    items: [
                        "artist_ftrack",
                        "manager_ftrack",
                        "manager_ftrack_actions",
                    ],
                }
            ],
        },
    ],
    Admin: [
        "system_introduction",
        {
            type: "category",
            label: "Getting Started",
            items: [
                "admin_builds",
                "admin_distribute",
                "admin_use",
                "admin_openpype_commands",
            ],
        },
        {
            type: "category",
            label: "Configuration",
            items: [
                "admin_settings",
                "admin_settings_system",
                "admin_settings_project_anatomy",
                {
                    type: "category",
                    label: "Project Settings",
                    items: [
                        "project_settings/settings_project_global",
                        "project_settings/settings_project_nuke",
                        "project_settings/settings_project_standalone"
                    ],
                },
            ],
        },
        {
            type: "category",
            label: "Modules",
            items: [
                "module_ftrack",
                "module_site_sync",
                "module_deadline",
                "module_muster",
                "module_clockify",
                "module_slack"
            ],
        },
        {
            type: "category",
            label: "Integrations",
            items: [
                "admin_hosts_blender",
                "admin_hosts_maya",
                "admin_hosts_resolve",
                "admin_hosts_harmony",
                "admin_hosts_aftereffects",
                "admin_hosts_tvpaint"
            ],
        },
        {
            type: "category",
            label: "Releases",
            items: ["changelog", "update_notes"],
        },
        {
            type: "category",
            collapsed: false,
            label: "2.0 legacy docs",
            items: [
                {
                    type: "category",
                    label: "Deployment",
                    items: [
                        "pype2/admin_getting_started",
                        "pype2/admin_install",
                        "pype2/admin_config",
                        "pype2/admin_ftrack",
                        "pype2/admin_hosts",
                        "pype2/admin_pype_commands",
                        "pype2/admin_setup_troubleshooting",
                    ],
                },
                {
                    type: "category",
                    label: "Configuration",
                    items: [
                        "pype2/admin_presets_nukestudio",
                        "pype2/admin_presets_ftrack",
                        "pype2/admin_presets_maya",
                        "pype2/admin_presets_plugins",
                        "pype2/admin_presets_tools",
                    ],
                },
            ],
        },
    ],
     Dev: [
        "dev_introduction",
        "dev_requirements",
        "dev_build",
        "dev_testing",
        "dev_contribute",
        {
            type: "category",
            label: "Hosts development",
            items: [
                "dev_publishing"
            ]
        }
     ]
};
