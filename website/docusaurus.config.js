module.exports = {
  title: 'PYPE',
  tagline: 'code . training . support',
  url: 'http://pype.club/',
  baseUrl: '/',
  organizationName: 'pypeclub',
  projectName: 'pypeclub.github.io',
  favicon: 'img/favicon/favicon.ico',
  onBrokenLinks: 'ignore',
  customFields: {
  },
  presets: [
    [
      '@docusaurus/preset-classic', {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css')
        }
      }
    ]
  ],
  themeConfig: {
    colorMode: {
      // "light" | "dark"
      defaultMode: 'light',

      // Hides the switch in the navbar
      // Useful if you want to support a single color mode
      disableSwitch: true
    },
    navbar: {
      style: 'dark',
      title: 'PYPE',
      logo: {
        src: 'img/favicon/P.png'
      },
      items: [
        {
          to: '/features',
          label: 'Features',
          position: 'left'
        }, {
          to: 'docs/artist_getting_started',
          label: 'User Docs',
          position: 'left'
        }, {
          to: 'docs/admin_getting_started',
          label: 'Admin Docs',
          position: 'left'
        }, {
          href: 'https://github.com/pypeclub',
          label: 'Github',
          position: 'right',
        }
      ]
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Pages',
          items: [
            {
              label: 'Index',
              to: '/',
            },
            {
              label: 'Features',
              to: 'features',
            },
          ],
        },
        {
          title: 'Docs',
          items: [
            {
              label: 'Artist',
              to: 'docs/artist_getting_started',
            },
            {
              label: 'Admin',
              to: 'docs/admin_getting_started',
            },
          ],
        },{
          title: 'Community',
          items: [
            {
              label: 'Avalon Chat',
              to: 'https://gitter.im/getavalon/Lobby',
            },
            {
              label: 'Pyblish Chat',
              to: 'https://gitter.im/pyblish/pyblish',
            },
            {
              label: 'Pype Chat',
              to: 'https://discord.gg/sFNPWXG',
            },
          ],
        },
      ],
      copyright: 'Copyright © 2020 Orbi Tools',
    },
    algolia: {
      apiKey: '5e01ee3bfbb744ca6f25d4b281ce38a9',
      indexName: 'pype',
      // Optional: see doc section bellow
      contextualSearch: true,
      // Optional: Algolia search parameters
      searchParameters: {},
    },
    googleAnalytics: {
      trackingID: 'G-HHJZ9VF0FG',
      // Optional fields.
      anonymizeIP: false, // Should IPs be anonymized?
    },
  },
  stylesheets: [
        'https://use.fontawesome.com/releases/v5.7.2/css/all.css'
    ],
};
